"""Viterbi-Kalman solver for serial MultiView delay gradients in AltAz space.

This module contains the numerical part of the delay MultiView rewrite.  The
primary calibrator is the zero point, so the fitted atmospheric delay plane has
no intercept.  For a secondary calibrator observation at time ``t_i``:

    y_i + n_i * ambiguity_spacing = H_i x_i + e_i
    H_i = [x_el_i, delta_az_i, 0, 0]
    x_i = [g_el, g_az, dg_el_dt, dg_az_dt]

``x_el`` is the selected primary-relative elevation coordinate: ordinary degree
difference for ``linear`` mapping, or raw ``csc(el_source) - csc(el_primary)``
for ``cosecant`` mapping.  ``delta_az`` is always in degrees relative to the
primary calibrator at the same station and scan time.  ``y_i`` is the total
delay in seconds.  The rate components are temporal derivatives of the two
delay gradients; they are inferred from the delay time series by the state
dynamics, not read from the exported SN rate columns.

The discrete ambiguity integer ``n_i`` is persistent per secondary calibrator.
Viterbi dynamic programming chooses the lowest-cost integer path while each
branch carries a Kalman state estimate.  After the integer path and outliers
are selected, a final Kalman pass and optional Rauch-Tung-Striebel smoother
produce the state series used by the GUI and target-delay export.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Dict, Iterable, List, Tuple

import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers

from .elevation_mapping import mapped_elevation_offset


iers.conf.auto_download = False


@dataclass
class ViterbiGradientSearchResult:
    """Result of the discrete ambiguity search plus its branch Kalman states."""

    integer_path: np.ndarray
    integer_tuple_path: np.ndarray
    corrected_observation: np.ndarray
    filtered_state_path: np.ndarray
    filtered_covariance_path: np.ndarray
    total_cost: float


@dataclass
class GradientSmootherResult:
    """Result of the final continuous-state Kalman/RTS fit."""

    state: np.ndarray
    covariance: np.ndarray
    fitted_observation: np.ndarray
    residual: np.ndarray
    standardized_residual: np.ndarray


@dataclass
class ViterbiKalmanGradientFit:
    """Complete solver result returned to :class:`plugin.core.mv.Antenna.Antenna`.

    ``state`` has columns ``[grad_el, grad_az, rate_grad_el, rate_grad_az]``.
    The first two columns are consumed for the target delay correction; the rate
    columns are retained so the dynamics and diagnostics remain inspectable.
    """

    integer_path: np.ndarray
    integer_tuple_path: np.ndarray
    corrected_observation: np.ndarray
    state: np.ndarray
    covariance: np.ndarray
    fitted_observation: np.ndarray
    residual: np.ndarray
    standardized_residual: np.ndarray
    outlier_mask: np.ndarray
    valid_mask: np.ndarray
    iterations: int
    search_result: ViterbiGradientSearchResult
    smoother_result: GradientSmootherResult


@dataclass
class _Branch:
    """One Viterbi branch: accumulated cost and latest Kalman posterior."""

    cost: float
    state: np.ndarray
    covariance: np.ndarray


def huber_cost(z: float, c: float = 3.0) -> float:
    """Robust quadratic/linear cost for a standardized residual."""
    az = abs(float(z))
    if az <= c:
        return az * az
    return 2.0 * c * az - c * c


def _as_float_array(name: str, value: Iterable[float]) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")
    if arr.size == 0:
        raise ValueError(f"{name} must not be empty.")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or infinite values.")
    return arr


def _validate_inputs(
    t: Iterable[float],
    source_id: Iterable[int],
    delta_el: Iterable[float],
    delta_az: Iterable[float],
    delay: Iterable[float],
    variance: Iterable[float],
    kalman_factor: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    t_arr = _as_float_array("t", t)
    src_arr = np.asarray(source_id, dtype=int)
    el_arr = _as_float_array("delta_el", delta_el)
    az_arr = _as_float_array("delta_az", delta_az)
    y_arr = _as_float_array("delay", delay)
    r_arr = _as_float_array("variance", variance)
    if not (len(t_arr) == len(src_arr) == len(el_arr) == len(az_arr) == len(y_arr) == len(r_arr)):
        raise ValueError("t, source_id, delta_el, delta_az, delay, and variance must have the same length.")
    if np.any(r_arr <= 0.0):
        raise ValueError("variance must contain positive values.")
    if kalman_factor <= 0.0:
        raise ValueError("kalman_factor must be positive.")
    return t_arr, src_arr, el_arr, az_arr, y_arr, r_arr


def _design_row(delta_el: float, delta_az: float) -> np.ndarray:
    """Observation row for an intercept-free mapped-elevation/AltAz plane."""
    return np.array([float(delta_el), float(delta_az), 0.0, 0.0], dtype=float)


def _state_transition(dt: float) -> np.ndarray:
    """Constant-gradient-rate transition for time spacing ``dt`` in days."""
    return np.array([
        [1.0, 0.0, float(dt), 0.0],
        [0.0, 1.0, 0.0, float(dt)],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=float)


def _process_noise(kalman_factor: float, dt: float) -> np.ndarray:
    """Return local-linear process noise for the two gradient axes.

    ``kalman_factor`` is the continuous white-noise acceleration scale for a
    gradient random walk.  The same 2x2 position/rate block is applied to the
    elevation-gradient and azimuth-gradient subspaces.
    """
    dt_abs = abs(float(dt))
    q = float(kalman_factor)
    block = q * np.array([
        [dt_abs ** 3 / 3.0, dt_abs ** 2 / 2.0],
        [dt_abs ** 2 / 2.0, dt_abs],
    ], dtype=float)
    out = np.zeros((4, 4), dtype=float)
    out[0, 0] = block[0, 0]
    out[0, 2] = block[0, 1]
    out[2, 0] = block[1, 0]
    out[2, 2] = block[1, 1]
    out[1, 1] = block[0, 0]
    out[1, 3] = block[0, 1]
    out[3, 1] = block[1, 0]
    out[3, 3] = block[1, 1]
    return out


def _initial_covariance(p0_gradient, variance: np.ndarray, delta_el: np.ndarray, delta_az: np.ndarray) -> np.ndarray:
    """Initial covariance for gradients/rates.

    When not explicitly fixed, the scale is derived from the median observation
    variance and the typical squared angular offset.  This keeps the first
    observation informative without requiring a public ``p0`` tuning knob.
    """
    if p0_gradient is not None:
        p0 = float(p0_gradient)
    else:
        h_norm2 = np.maximum(delta_el * delta_el + delta_az * delta_az, 1.0e-12)
        p0 = 1.0e6 * float(np.median(variance)) / float(np.median(h_norm2))
    if p0 <= 0.0:
        raise ValueError("viterbi_p0_gradient must be positive or null.")
    return np.eye(4, dtype=float) * p0


def _scalar_update(state_pred: np.ndarray, cov_pred: np.ndarray, h: np.ndarray, y: float, r: float):
    """Joseph-form scalar Kalman measurement update.

    The Joseph covariance update is a little more expensive than the compact
    formula, but it is more numerically stable for small delay variances.
    """
    s = float(h @ cov_pred @ h + r)
    if not np.isfinite(s) or s <= 0.0:
        raise ValueError("Innovation covariance is not positive.")
    innovation = float(y - h @ state_pred)
    k = cov_pred @ h / s
    state_update = state_pred + k * innovation
    eye = np.eye(cov_pred.shape[0], dtype=float)
    kh = np.outer(k, h)
    cov_update = (eye - kh) @ cov_pred @ (eye - kh).T + np.outer(k, k) * r
    standardized = innovation / np.sqrt(s)
    return state_update, cov_update, innovation, s, standardized


def _validate_initial_integer(value, states: np.ndarray) -> int:
    value = int(value)
    if value not in states:
        raise ValueError("Initial ambiguity integer must be in viterbi_integer_states.")
    return value


def _initial_tuples(states: np.ndarray, sources: np.ndarray, fix_initial_integer) -> List[Tuple[int, ...]]:
    """Build allowed initial ambiguity tuples.

    A tuple stores one persistent integer per secondary calibrator.  If the GUI
    fixes the initial integers, the Viterbi lattice starts from only that tuple;
    otherwise all combinations in ``states`` are considered.
    """
    n_sources = len(sources)
    if fix_initial_integer is not None:
        if isinstance(fix_initial_integer, dict):
            initial_map = {int(key): int(value) for key, value in fix_initial_integer.items()}
            return [tuple(_validate_initial_integer(initial_map.get(int(src), 0), states) for src in sources)]
        if isinstance(fix_initial_integer, (list, tuple, np.ndarray)):
            fix_values = list(fix_initial_integer)
            if len(fix_values) != n_sources:
                raise ValueError("Per-source initial ambiguity list must match the number of sources.")
            return [tuple(_validate_initial_integer(value, states) for value in fix_values)]
        fix = _validate_initial_integer(fix_initial_integer, states)
        return [tuple([fix] * n_sources)]
    return [tuple(int(value) for value in item) for item in product(states, repeat=n_sources)]


def viterbi_gradient_search(
    t: Iterable[float],
    source_id: Iterable[int],
    delta_el: Iterable[float],
    delta_az: Iterable[float],
    delay: Iterable[float],
    variance: Iterable[float],
    kalman_factor: float,
    ambiguity_spacing: float,
    integer_states: Iterable[int] = range(-3, 4),
    max_jump: int = 1,
    jump_penalty: float = 25.0,
    robust: bool = True,
    huber_c: float = 3.0,
    valid_mask: Iterable[bool] | None = None,
    fix_initial_integer=0,
    p0_gradient=None,
) -> ViterbiGradientSearchResult:
    """Choose persistent per-calibrator ambiguity integers by Viterbi search.

    Parameters use the same units as the module-level model.  ``integer_states``
    is the set of allowed ambiguity integers, and ``max_jump`` limits how much
    the integer of the currently observed calibrator may change at one step.

    The observation cost is ``Huber(z) + log(S)`` by default, where ``z`` is the
    standardized innovation and ``S`` is its variance.  ``jump_penalty`` adds a
    fixed cost whenever the active calibrator changes integer state, favoring
    persistent ambiguity corrections unless the data strongly prefer a slip.
    """
    t_arr, src_arr, el_arr, az_arr, y_arr, r_arr = _validate_inputs(
        t, source_id, delta_el, delta_az, delay, variance, kalman_factor
    )
    if ambiguity_spacing <= 0.0:
        raise ValueError("ambiguity_spacing must be positive.")
    states = np.asarray(list(integer_states), dtype=int)
    if states.size == 0 or np.unique(states).size != states.size:
        raise ValueError("viterbi_integer_states must contain unique integers.")
    if max_jump < 0:
        raise ValueError("viterbi_max_jump must be >= 0.")
    if jump_penalty < 0.0:
        raise ValueError("viterbi_jump_penalty must be >= 0.")
    if huber_c <= 0.0:
        raise ValueError("viterbi_huber_c must be positive.")

    n_obs = len(y_arr)
    valid = np.ones(n_obs, dtype=bool) if valid_mask is None else np.asarray(valid_mask, dtype=bool)
    if valid.shape != (n_obs,):
        raise ValueError("valid_mask must have the same length as delay.")
    if not np.any(valid):
        raise ValueError("At least one valid observation is required.")

    sources = np.asarray(sorted(np.unique(src_arr)), dtype=int)
    src_to_idx = {int(src): idx for idx, src in enumerate(sources)}
    src_idx = np.array([src_to_idx[int(src)] for src in src_arr], dtype=int)
    p0 = _initial_covariance(p0_gradient, r_arr[valid], el_arr[valid], az_arr[valid])

    branches: Dict[Tuple[int, ...], _Branch] = {}
    h0 = _design_row(el_arr[0], az_arr[0])
    for tpl in _initial_tuples(states, sources, fix_initial_integer):
        state_pred = np.zeros(4, dtype=float)
        cov_pred = p0.copy()
        cost = 0.0
        if valid[0]:
            corrected_y = y_arr[0] + tpl[src_idx[0]] * ambiguity_spacing
            state_update, cov_update, _, s, z = _scalar_update(state_pred, cov_pred, h0, corrected_y, r_arr[0])
            obs_cost = huber_cost(z, huber_c) if robust else z * z
            cost = float(obs_cost + np.log(s))
        else:
            state_update = state_pred
            cov_update = cov_pred
        branches[tpl] = _Branch(cost=cost, state=state_update, covariance=cov_update)

    backpointers: List[Dict[Tuple[int, ...], Tuple[int, ...]]] = [{} for _ in range(n_obs)]
    histories: List[Dict[Tuple[int, ...], _Branch]] = [branches]

    for i in range(1, n_obs):
        next_branches: Dict[Tuple[int, ...], _Branch] = {}
        next_back: Dict[Tuple[int, ...], Tuple[int, ...]] = {}
        h = _design_row(el_arr[i], az_arr[i])
        dt = float(t_arr[i] - t_arr[i - 1])
        f_i = _state_transition(dt)
        q_i = _process_noise(kalman_factor, dt)
        current_source_idx = src_idx[i]
        # Only the currently observed calibrator can change its integer at this
        # observation.  Integers for the other calibrators persist in the tuple.
        for prev_tuple, prev_branch in branches.items():
            prev_source_integer = prev_tuple[current_source_idx]
            for candidate in states:
                candidate = int(candidate)
                if abs(candidate - prev_source_integer) > max_jump:
                    continue
                curr_tuple_list = list(prev_tuple)
                curr_tuple_list[current_source_idx] = candidate
                curr_tuple = tuple(curr_tuple_list)

                state_pred = f_i @ prev_branch.state
                cov_pred = f_i @ prev_branch.covariance @ f_i.T + q_i
                if valid[i]:
                    corrected_y = y_arr[i] + candidate * ambiguity_spacing
                    state_update, cov_update, _, s, z = _scalar_update(
                        state_pred, cov_pred, h, corrected_y, r_arr[i]
                    )
                    obs_cost = huber_cost(z, huber_c) if robust else z * z
                    obs_cost = float(obs_cost + np.log(s))
                else:
                    state_update = state_pred
                    cov_update = cov_pred
                    obs_cost = 0.0
                transition_cost = float(jump_penalty) if candidate != prev_source_integer else 0.0
                total_cost = prev_branch.cost + obs_cost + transition_cost
                old = next_branches.get(curr_tuple)
                if old is None or total_cost < old.cost:
                    next_branches[curr_tuple] = _Branch(total_cost, state_update, cov_update)
                    next_back[curr_tuple] = prev_tuple
        if not next_branches:
            raise RuntimeError("No valid Viterbi-Kalman path found.")
        branches = next_branches
        backpointers[i] = next_back
        histories.append(branches)

    # Backtrack the cheapest final branch to recover the full integer history.
    final_tuple = min(branches, key=lambda key: branches[key].cost)
    total_cost = float(branches[final_tuple].cost)
    tuple_path: List[Tuple[int, ...]] = [final_tuple]
    for i in range(n_obs - 1, 0, -1):
        tuple_path.append(backpointers[i][tuple_path[-1]])
    tuple_path = list(reversed(tuple_path))

    integer_tuple_path = np.asarray(tuple_path, dtype=int)
    integer_path = np.array([integer_tuple_path[i, src_idx[i]] for i in range(n_obs)], dtype=int)
    corrected = y_arr + integer_path * ambiguity_spacing
    filtered_state = np.vstack([histories[i][tuple_path[i]].state for i in range(n_obs)])
    filtered_cov = np.stack([histories[i][tuple_path[i]].covariance for i in range(n_obs)])

    return ViterbiGradientSearchResult(
        integer_path=integer_path,
        integer_tuple_path=integer_tuple_path,
        corrected_observation=corrected,
        filtered_state_path=filtered_state,
        filtered_covariance_path=filtered_cov,
        total_cost=total_cost,
    )


def kalman_filter_rts_gradient(
    t: Iterable[float],
    delta_el: Iterable[float],
    delta_az: Iterable[float],
    delay: Iterable[float],
    variance: Iterable[float],
    kalman_factor: float,
    valid_mask: Iterable[bool] | None = None,
    p0_gradient=None,
    smooth: bool = True,
) -> GradientSmootherResult:
    """Fit the continuous gradient state for a fixed ambiguity-corrected delay.

    ``valid_mask`` removes outliers from measurement updates while still
    propagating the state through their timestamps.  With ``smooth=True`` the
    forward Kalman estimates are followed by a Rauch-Tung-Striebel backward pass
    so each scan can use information from the whole time series.
    """
    t_arr = _as_float_array("t", t)
    el_arr = _as_float_array("delta_el", delta_el)
    az_arr = _as_float_array("delta_az", delta_az)
    y_arr = _as_float_array("delay", delay)
    r_arr = _as_float_array("variance", variance)
    if not (len(t_arr) == len(el_arr) == len(az_arr) == len(y_arr) == len(r_arr)):
        raise ValueError("t, delta_el, delta_az, delay, and variance must have the same length.")
    if np.any(r_arr <= 0.0):
        raise ValueError("variance must contain positive values.")
    valid = np.ones(len(y_arr), dtype=bool) if valid_mask is None else np.asarray(valid_mask, dtype=bool)
    if valid.shape != (len(y_arr),):
        raise ValueError("valid_mask must have the same length as delay.")
    if not np.any(valid):
        raise ValueError("At least one valid observation is required.")

    n_obs = len(y_arr)
    state_pred = np.zeros((n_obs, 4), dtype=float)
    cov_pred = np.zeros((n_obs, 4, 4), dtype=float)
    state_filt = np.zeros((n_obs, 4), dtype=float)
    cov_filt = np.zeros((n_obs, 4, 4), dtype=float)

    state_filt[0] = np.zeros(4, dtype=float)
    cov_filt[0] = _initial_covariance(p0_gradient, r_arr[valid], el_arr[valid], az_arr[valid])
    state_pred[0] = state_filt[0]
    cov_pred[0] = cov_filt[0]
    if valid[0]:
        h = _design_row(el_arr[0], az_arr[0])
        state_filt[0], cov_filt[0], _, _, _ = _scalar_update(state_pred[0], cov_pred[0], h, y_arr[0], r_arr[0])

    for i in range(1, n_obs):
        dt = float(t_arr[i] - t_arr[i - 1])
        f_i = _state_transition(dt)
        q_i = _process_noise(kalman_factor, dt)
        state_pred[i] = f_i @ state_filt[i - 1]
        cov_pred[i] = f_i @ cov_filt[i - 1] @ f_i.T + q_i
        if valid[i]:
            h = _design_row(el_arr[i], az_arr[i])
            state_filt[i], cov_filt[i], _, _, _ = _scalar_update(
                state_pred[i], cov_pred[i], h, y_arr[i], r_arr[i]
            )
        else:
            state_filt[i] = state_pred[i]
            cov_filt[i] = cov_pred[i]

    if smooth:
        state_out = state_filt.copy()
        cov_out = cov_filt.copy()
        for i in range(n_obs - 2, -1, -1):
            dt = float(t_arr[i + 1] - t_arr[i])
            f_next = _state_transition(dt)
            q_next = _process_noise(kalman_factor, dt)
            p_next_pred = f_next @ cov_filt[i] @ f_next.T + q_next
            gain = cov_filt[i] @ f_next.T @ np.linalg.pinv(p_next_pred)
            state_out[i] = state_filt[i] + gain @ (state_out[i + 1] - state_pred[i + 1])
            cov_out[i] = cov_filt[i] + gain @ (cov_out[i + 1] - p_next_pred) @ gain.T
    else:
        state_out = state_filt
        cov_out = cov_filt

    fitted = np.array([_design_row(el_arr[i], az_arr[i]) @ state_out[i] for i in range(n_obs)])
    residual = y_arr - fitted
    obs_var = np.array([
        _design_row(el_arr[i], az_arr[i]) @ cov_out[i] @ _design_row(el_arr[i], az_arr[i]) + r_arr[i]
        for i in range(n_obs)
    ])
    standardized = residual / np.sqrt(np.maximum(obs_var, 1.0e-30))

    return GradientSmootherResult(
        state=state_out,
        covariance=cov_out,
        fitted_observation=fitted,
        residual=residual,
        standardized_residual=standardized,
    )


def fit_viterbi_kalman_gradient(
    t: Iterable[float],
    source_id: Iterable[int],
    delta_el: Iterable[float],
    delta_az: Iterable[float],
    delay: Iterable[float],
    variance: Iterable[float],
    kalman_factor: float,
    ambiguity_spacing: float,
    integer_states: Iterable[int] = range(-3, 4),
    max_jump: int = 1,
    jump_penalty: float = 25.0,
    robust: bool = True,
    huber_c: float = 3.0,
    z_out: float = 5.0,
    max_outlier_iterations: int = 2,
    fix_initial_integer=0,
    p0_gradient=None,
    rts_smoothing: bool = True,
) -> ViterbiKalmanGradientFit:
    """Run ambiguity search, automatic outlier rejection, and final smoothing.

    The integer path is re-estimated after each outlier pass because an extreme
    point can otherwise bias both the continuous gradients and the discrete
    ambiguity choice.  The returned ``outlier_mask`` is later converted into
    automatic per-IF flags by :meth:`Antenna.delay_multiview`.
    """
    t_arr, src_arr, el_arr, az_arr, y_arr, r_arr = _validate_inputs(
        t, source_id, delta_el, delta_az, delay, variance, kalman_factor
    )
    if z_out <= 0.0:
        raise ValueError("viterbi_z_out must be positive.")
    if max_outlier_iterations < 0:
        raise ValueError("viterbi_max_outlier_iterations must be >= 0.")

    valid = np.ones(len(y_arr), dtype=bool)
    outliers = np.zeros(len(y_arr), dtype=bool)
    search = None
    smoother = None
    iteration = 0
    for iteration in range(max_outlier_iterations + 1):
        search = viterbi_gradient_search(
            t_arr, src_arr, el_arr, az_arr, y_arr, r_arr, kalman_factor, ambiguity_spacing,
            integer_states=integer_states,
            max_jump=max_jump,
            jump_penalty=jump_penalty,
            robust=robust,
            huber_c=huber_c,
            valid_mask=valid,
            fix_initial_integer=fix_initial_integer,
            p0_gradient=p0_gradient,
        )
        smoother = kalman_filter_rts_gradient(
            t_arr, el_arr, az_arr, search.corrected_observation, r_arr, kalman_factor,
            valid_mask=valid,
            p0_gradient=p0_gradient,
            smooth=rts_smoothing,
        )
        if iteration >= max_outlier_iterations:
            break
        # Flag only newly large standardized residuals, then repeat the full
        # Viterbi+Kalman fit on the remaining observations.
        candidate = outliers.copy()
        candidate[valid] = np.abs(smoother.standardized_residual[valid]) > z_out
        new_outliers = candidate & ~outliers
        outliers = candidate
        valid = ~outliers
        if not np.any(new_outliers):
            break

    # One final pass ensures the returned state is exactly consistent with the
    # final outlier mask, even when the loop stopped immediately after a change.
    search = viterbi_gradient_search(
        t_arr, src_arr, el_arr, az_arr, y_arr, r_arr, kalman_factor, ambiguity_spacing,
        integer_states=integer_states,
        max_jump=max_jump,
        jump_penalty=jump_penalty,
        robust=robust,
        huber_c=huber_c,
        valid_mask=valid,
        fix_initial_integer=fix_initial_integer,
        p0_gradient=p0_gradient,
    )
    smoother = kalman_filter_rts_gradient(
        t_arr, el_arr, az_arr, search.corrected_observation, r_arr, kalman_factor,
        valid_mask=valid,
        p0_gradient=p0_gradient,
        smooth=rts_smoothing,
    )

    return ViterbiKalmanGradientFit(
        integer_path=search.integer_path,
        integer_tuple_path=search.integer_tuple_path,
        corrected_observation=search.corrected_observation,
        state=smoother.state,
        covariance=smoother.covariance,
        fitted_observation=smoother.fitted_observation,
        residual=smoother.residual,
        standardized_residual=smoother.standardized_residual,
        outlier_mask=outliers,
        valid_mask=valid,
        iterations=iteration + 1,
        search_result=search,
        smoother_result=smoother,
    )


def altaz_offsets(
    source_ra: float,
    source_dec: float,
    primary_ra: float,
    primary_dec: float,
    times_day: Iterable[float],
    obs_jd0: float,
    station_xyz: Iterable[float],
    elevation_mapping: str = "linear",
) -> np.ndarray:
    """Compute source-primary AltAz offsets for each scan time.

    ``station_xyz`` is geocentric ITRF-like X/Y/Z in meters.  ``times_day`` is
    the AIPS/SN relative time in days and ``obs_jd0`` is the observation JD
    origin.  The first coordinate is either ordinary elevation difference in
    degrees or raw cosecant-elevation mapping difference, depending on
    ``elevation_mapping``.  The azimuth difference is wrapped to
    ``[-180, 180)`` degrees so a source pair crossing north does not create a
    spurious large separation.
    """
    times_arr = _as_float_array("times_day", times_day)
    xyz = np.asarray(station_xyz, dtype=float)
    if xyz.shape != (3,) or not np.all(np.isfinite(xyz)):
        raise ValueError("station_xyz must contain finite X/Y/Z geocentric coordinates.")
    location = EarthLocation.from_geocentric(xyz[0] * u.m, xyz[1] * u.m, xyz[2] * u.m)
    obstime = Time(float(obs_jd0) + times_arr, format="jd", scale="utc")
    frame = AltAz(obstime=obstime, location=location)
    source = SkyCoord(float(source_ra), float(source_dec), unit=u.deg, frame="icrs").transform_to(frame)
    primary = SkyCoord(float(primary_ra), float(primary_dec), unit=u.deg, frame="icrs").transform_to(frame)
    delta_el = mapped_elevation_offset(
        source.alt.to_value(u.deg),
        primary.alt.to_value(u.deg),
        elevation_mapping,
    )
    delta_az = Angle(source.az - primary.az).wrap_at(180 * u.deg).to_value(u.deg)
    return np.column_stack([delta_el, delta_az])
