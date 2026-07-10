"""
class for antennas
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""
import numpy as np
import pandas as pd
import copy
import ast
import matplotlib.pyplot as plt
# import scipy.interpolate as interp
# import pdb
from typing import List

from .Calibrator import Calibrator
from .elevation_mapping import (
    LINEAR_ELEVATION_MAPPING,
    elevation_axis_label,
    elevation_coordinate_label,
    gradient_axis_label,
    normalize_elevation_mapping,
)
from .viterbi_kalman_altaz import altaz_offsets, fit_viterbi_kalman_gradient
# from .rodrigues_rotation import rodrigues_rotation


class Antenna:
    def __init__(
        self,
        antenna_id,
        antenna_name,
        data=None,
        calibrators: List[Calibrator]=None,
        if_freq=None,
        no_if=1,
        station_xyz=None,
        obs_jd0=None,
        primary=None,
        target=None,
    ):
        """
        Antenna-local state for the MultiView GUI and delay solver.

        ``data`` is the per-antenna SN export for secondary calibrators.  Delay
        columns are named ``d{if_id}``, phase columns ``p{if_id}``, and
        ``weight`` is the SN weight used to form observation variances.

        ``station_xyz``, ``obs_jd0``, ``primary``, and ``target`` are required
        by the AltAz solver.  They let each scan use the current station-local
        mapped elevation/azimuth coordinates instead of static sky-plane
        coordinates.

        :param antenna_id: antenna id
        :param antenna_name: antenna name
        :param data: input time series
        :param calibrators: secondary calibrator list
        """
        self.colors = plt.rcParams['axes.prop_cycle'].by_key()['color']  # default color sequence used by plt

        self.id = antenna_id
        self.name = antenna_name
        if data is None:
            data = pd.DataFrame(columns=['calsour', 'x', 'y', 't'])
        if calibrators is None:
            calibrators = []
        self.original_data = data.copy(deep=True)  # without flag and manual wrap
        self.original_data.reset_index(drop=True, inplace=True)
        self.data = self.original_data.copy(deep=True)  # flagged/wrapped data
        self.secondary_calibrators = calibrators
        self.adjust_info = pd.DataFrame(data=np.zeros(shape=(self.original_data.index.size, 2)),
                                        columns=['flag', 'wrap']).astype({'flag': int, 'wrap': int})
        self.t_flag_info = []
        self.mv_result = None
        self.mv_t = None
        # record accumulated wrap during auto mv procedure
        self.accu_info = pd.DataFrame(data=np.zeros(shape=(self.original_data.index.size, 1)),
                                      columns=['accu']).astype({'accu': float})
        self.accu_data = None  # data with flag+wrap+accu adjustment

        self.target_pos = None
        self.station_xyz = None if station_xyz is None else np.asarray(station_xyz, dtype=float)
        self.obs_jd0 = obs_jd0
        self.primary = primary
        self.target = target
        self._source_by_id = {int(cal.id): cal for cal in self.secondary_calibrators}
        self.elevation_mapping = "linear"

        self.reverse = False

        self.delay_if_ids = list(range(int(no_if)))
        self.if_freq = self._normalize_if_freq(if_freq, self.delay_if_ids)
        delay_adjust_columns = [f'flag{if_id}' for if_id in self.delay_if_ids] + [f'w{if_id}' for if_id in self.delay_if_ids]
        self.delay_adjust_info = pd.DataFrame(
            data=np.zeros(shape=(self.original_data.index.size, len(delay_adjust_columns))),
            columns=delay_adjust_columns,
        )
        dtype_map = {f'flag{if_id}': int for if_id in self.delay_if_ids}
        dtype_map.update({f'w{if_id}': int for if_id in self.delay_if_ids})
        self.delay_adjust_info = self.delay_adjust_info.astype(dtype_map)
        self.delay_auto_adjust_info = pd.DataFrame(
            data=np.zeros(shape=(self.original_data.index.size, len(delay_adjust_columns))),
            columns=delay_adjust_columns,
        ).astype(dtype_map)
        self.delay_t_flag_info = []
        self.delay_mv_result = None
        self.delay_mv_t = None
        self.delay_mv_t_by_if = {}
        self.delay_fit_info = {}

        # how the z axis is scaled for sMV
        max_xy = 0.
        for calibrator in self.secondary_calibrators:
            cal_max_xy = max(abs(calibrator.dx), abs(calibrator.dy))
            max_xy = max_xy if max_xy > cal_max_xy else cal_max_xy
        delay_columns = [f'd{if_id}' for if_id in self.delay_if_ids if f'd{if_id}' in self.data.columns]
        max_z = self.data[delay_columns].abs().max().max() if delay_columns else 0.
        self.z_scale = max_xy / max_z if max_z not in (0, None) and np.isfinite(max_z) else 1.0

        self.delay_scale = {
            if_id: float(self.if_freq.get(if_id, 1.0)) * 2e9 * np.pi
            for if_id in self.delay_if_ids
        }
        self.delay_target_if = {}
        self.delay_average = np.array([])
        self.delay_average_t = np.array([])

    @staticmethod
    def _normalize_if_freq(if_freq, delay_if_ids):
        if if_freq is None:
            return {if_id: 1.0 for if_id in delay_if_ids}
        if np.isscalar(if_freq):
            return {if_id: float(if_freq) for if_id in delay_if_ids}
        freq_list = list(if_freq)
        out = {}
        for if_id in delay_if_ids:
            if if_id < len(freq_list):
                out[if_id] = float(freq_list[if_id])
            elif freq_list:
                out[if_id] = float(freq_list[-1])
            else:
                out[if_id] = 1.0
        return out

    def _flag_col(self, if_id):
        return f'flag{if_id}'

    def _wrap_col(self, if_id):
        return f'w{if_id}'

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "y", "on")
        return bool(value)

    @staticmethod
    def _parse_optional(value, dtype=float):
        if value is None:
            return None
        if isinstance(value, str) and value.strip().lower() in ("", "none", "null"):
            return None
        return dtype(value)

    @staticmethod
    def _parse_integer_states(value):
        if isinstance(value, str):
            value = ast.literal_eval(value)
        if np.isscalar(value):
            radius = int(value)
            if radius < 0:
                raise ValueError("viterbi_integer_states radius must be >= 0.")
            return list(range(-radius, radius + 1))
        return [int(item) for item in value]

    @staticmethod
    def _parse_initial_integer(value):
        if value is None:
            return None
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("", "none", "null"):
                return None
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return int(value)
        if isinstance(value, dict):
            return {int(key): int(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, np.ndarray)):
            return [int(item) for item in value]
        return int(value)

    @staticmethod
    def _source_ra_dec(source):
        if source is None:
            raise ValueError("Source metadata is not available.")
        if isinstance(source, dict):
            return float(source["RA"]), float(source["DEC"])
        return float(source.ra), float(source.dec)

    def source_altaz_offsets(self, source, times, elevation_mapping=None):
        """Return primary-relative solver coordinates for a source.

        The offsets are recomputed for each requested scan time because the
        station AltAz frame changes as the Earth rotates.  The first coordinate
        follows the selected elevation mapping, while azimuth remains a wrapped
        degree difference.
        """
        if self.primary is None or self.station_xyz is None or self.obs_jd0 is None:
            raise ValueError("Primary calibrator, station coordinates, and observation JD are required for AltAz MV.")
        if elevation_mapping is None:
            elevation_mapping = self.elevation_mapping
        source_ra, source_dec = self._source_ra_dec(source)
        primary_ra, primary_dec = self._source_ra_dec(self.primary)
        return altaz_offsets(
            source_ra,
            source_dec,
            primary_ra,
            primary_dec,
            times,
            self.obs_jd0,
            self.station_xyz,
            elevation_mapping=elevation_mapping,
        )

    def add_altaz_offsets(self, data_in, elevation_mapping=None):
        """Add per-row solver coordinates and true angular separation.

        ``delta_el`` stores the selected first coordinate, which may be raw
        cosecant elevation.  ``theta_deg`` is always computed from ordinary
        linear AltAz offsets so separation-dependent weighting remains tied to
        real source-primary angular distance.
        """
        if elevation_mapping is None:
            elevation_mapping = self.elevation_mapping
        data_out = data_in.copy(deep=True)
        data_out["delta_el"] = np.nan
        data_out["delta_az"] = np.nan
        data_out["theta_deg"] = np.nan
        if data_out.empty:
            return data_out
        for calsour in data_out["calsour"].dropna().unique():
            source = self._source_by_id.get(int(calsour))
            if source is None:
                continue
            mask = data_out["calsour"].astype(int) == int(calsour)
            offsets = self.source_altaz_offsets(source, data_out.loc[mask, "t"].to_numpy(), elevation_mapping)
            linear_offsets = offsets
            if normalize_elevation_mapping(elevation_mapping) != LINEAR_ELEVATION_MAPPING:
                # The solver coordinate may be non-linear, but reliability
                # weighting should use true angular separation in degrees.
                linear_offsets = self.source_altaz_offsets(
                    source,
                    data_out.loc[mask, "t"].to_numpy(),
                    LINEAR_ELEVATION_MAPPING,
                )
            data_out.loc[mask, ["delta_el", "delta_az"]] = offsets
            data_out.loc[mask, "theta_deg"] = np.hypot(linear_offsets[:, 0], linear_offsets[:, 1])
        return data_out

    def elevation_axis_label(self):
        """Return the first-coordinate label for plots."""
        return elevation_axis_label(self.elevation_mapping)

    @staticmethod
    def effective_delay_variance(unit_weight_variance, weight, theta_deg, separation_noise=0.0):
        """Observation variance including optional separation-dependent noise.

        Formula:

            unit_weight_variance * (1 / weight + (separation_noise * theta_deg)^2)

        ``separation_noise`` is unitless relative to ``unit_weight_variance``;
        setting it to zero recovers the previous SN-weight-only variance.
        """
        separation_noise = float(separation_noise)
        if separation_noise < 0.0:
            raise ValueError("separation_noise must be >= 0.")
        return float(unit_weight_variance) * (
            1.0 / np.asarray(weight, dtype=float)
            + (separation_noise * np.asarray(theta_deg, dtype=float)) ** 2
        )

    def delay_multiview(
        self,
        kalman_factor=1.0e-14,
        unit_weight_variance=4.0e-22,
        rts_smoothing=True,
        viterbi_integer_states=3,
        viterbi_max_jump=1,
        viterbi_jump_penalty=25.0,
        viterbi_robust=True,
        viterbi_huber_c=3.0,
        viterbi_z_out=4.0,
        viterbi_max_outlier_iterations=2,
        viterbi_fix_initial_integer=0,
        viterbi_p0_gradient=None,
        elevation_mapping="linear",
        separation_noise=0.0,
        progress_callback=None,
    ):
        """
        Solve delay MultiView gradients independently for each IF.

        The primary calibrator is the zero point.  For each secondary-calibrator
        row and IF, this method builds a total-delay observable in seconds,
        computes current primary-relative mapped-elevation/AltAz coordinates,
        and calls the Viterbi-Kalman solver for the state

            [grad_el, grad_az, rate_grad_el, rate_grad_az].

        The scalar observation variance is built from SN weight plus an optional
        separation-dependent term based on true linear angular separation.
        ``unit_weight_variance`` is kept fixed by ``solver_config`` because only
        relative weights matter for the current exported MV delay.  The
        ambiguity spacing is one IF phase wrap, ``1 / if_freq_hz``.

        The returned gradients are evaluated at the target AltAz offset for the
        same times, then the IF-specific target delays are interpolated to the
        first valid IF and averaged.  Output compatibility is preserved by
        saving only ``t`` and averaged ``mbdelay`` downstream.
        """
        def report(message, current=None, total=None):
            if progress_callback is not None:
                progress_callback(message, current, total)

        if self.original_data.empty:
            report("No delay data available", 1, 1)
            self.delay_mv_result = {}
            self.delay_mv_t = np.array([])
            self.delay_mv_t_by_if = {}
            self.delay_target_if = {}
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return
        n_if = len(self.delay_if_ids)
        progress_total = max(1, n_if * 3 + 2)
        progress_current = 0
        report("Preparing delay data", progress_current, progress_total)
        self.delay_auto_reset()
        self.update_delay_data()
        if self.data.empty or not self.delay_if_ids:
            report("No unflagged delay data available", progress_total, progress_total)
            self.delay_mv_result = {}
            self.delay_mv_t = np.array([])
            self.delay_mv_t_by_if = {}
            self.delay_target_if = {}
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return

        kalman_factor = float(kalman_factor)
        unit_weight_variance = float(unit_weight_variance)
        if unit_weight_variance <= 0.0:
            raise ValueError("unit_weight_variance must be positive.")
        rts_smoothing = self._parse_bool(rts_smoothing)
        viterbi_integer_states = self._parse_integer_states(viterbi_integer_states)
        viterbi_max_jump = int(viterbi_max_jump)
        viterbi_jump_penalty = float(viterbi_jump_penalty)
        viterbi_robust = self._parse_bool(viterbi_robust)
        viterbi_huber_c = float(viterbi_huber_c)
        viterbi_z_out = float(viterbi_z_out)
        viterbi_max_outlier_iterations = int(viterbi_max_outlier_iterations)
        viterbi_fix_initial_integer = self._parse_initial_integer(viterbi_fix_initial_integer)
        viterbi_p0_gradient = self._parse_optional(viterbi_p0_gradient, float)
        self.elevation_mapping = normalize_elevation_mapping(elevation_mapping)
        separation_noise = float(separation_noise)
        if separation_noise < 0.0:
            raise ValueError("separation_noise must be >= 0.")

        delay_results = {}
        delay_t_by_if = {}
        fit_info = {}
        for if_num, if_id in enumerate(self.delay_if_ids, start=1):
            report(f"IF {if_num}/{n_if}: preparing observations", progress_current, progress_total)
            self.update_delay_data(if_id)
            if self.data.empty:
                delay_results[if_id] = np.empty((0, 4))
                delay_t_by_if[if_id] = np.array([])
                progress_current += 3
                report(f"IF {if_num}/{n_if}: skipped", progress_current, progress_total)
                continue
            if "weight" not in self.data.columns:
                self.data["weight"] = 1.0
            # Fold the exported phase back into the delay observable so the
            # solver receives a phase-consistent total delay in seconds.
            data_corrected = self._correct_delay_with_phase(self.data.copy(deep=True), if_id)
            data_view = data_corrected[["calsour", "t", "total_delay", "weight", "_orig_index"]].copy(deep=True)
            data_view = self.add_altaz_offsets(data_view, self.elevation_mapping)
            finite = (
                np.isfinite(data_view["total_delay"].to_numpy(dtype=float))
                & np.isfinite(data_view["weight"].to_numpy(dtype=float))
                & (data_view["weight"].to_numpy(dtype=float) > 0.0)
                & np.isfinite(data_view["delta_el"].to_numpy(dtype=float))
                & np.isfinite(data_view["delta_az"].to_numpy(dtype=float))
                & np.isfinite(data_view["theta_deg"].to_numpy(dtype=float))
            )
            data_view = data_view.loc[finite].copy(deep=True)
            data_view.reset_index(drop=True, inplace=True)
            if data_view.empty:
                delay_results[if_id] = np.empty((0, 4))
                delay_t_by_if[if_id] = np.array([])
                progress_current += 3
                report(f"IF {if_num}/{n_if}: skipped", progress_current, progress_total)
                continue
            progress_current += 1
            report(f"IF {if_num}/{n_if}: fitting Viterbi-Kalman", progress_current, progress_total)

            data_solve = data_view.iloc[::-1].copy(deep=True) if self.reverse else data_view
            ambiguity_spacing = 1.0 / (self.if_freq.get(if_id, 1.0) * 1e9)
            variance = self.effective_delay_variance(
                unit_weight_variance,
                data_solve["weight"].to_numpy(dtype=float),
                data_solve["theta_deg"].to_numpy(dtype=float),
                separation_noise,
            )
            fit = fit_viterbi_kalman_gradient(
                data_solve["t"].to_numpy(dtype=float),
                data_solve["calsour"].to_numpy(dtype=int),
                data_solve["delta_el"].to_numpy(dtype=float),
                data_solve["delta_az"].to_numpy(dtype=float),
                data_solve["total_delay"].to_numpy(dtype=float),
                variance,
                kalman_factor,
                ambiguity_spacing,
                integer_states=viterbi_integer_states,
                max_jump=viterbi_max_jump,
                jump_penalty=viterbi_jump_penalty,
                robust=viterbi_robust,
                huber_c=viterbi_huber_c,
                z_out=viterbi_z_out,
                max_outlier_iterations=viterbi_max_outlier_iterations,
                fix_initial_integer=viterbi_fix_initial_integer,
                p0_gradient=viterbi_p0_gradient,
                rts_smoothing=rts_smoothing,
            )
            progress_current += 1
            report(f"IF {if_num}/{n_if}: storing result", progress_current, progress_total)
            if self.reverse:
                mv_res = fit.state[::-1]
                mv_t = data_solve["t"].to_numpy(dtype=float)[::-1]
                integer_path = fit.integer_path[::-1]
                orig_index = data_solve["_orig_index"].to_numpy(dtype=int)[::-1]
                outlier_mask = fit.outlier_mask[::-1]
            else:
                mv_res = fit.state
                mv_t = data_solve["t"].to_numpy(dtype=float)
                integer_path = fit.integer_path
                orig_index = data_solve["_orig_index"].to_numpy(dtype=int)
                outlier_mask = fit.outlier_mask
            delay_results[if_id] = mv_res
            delay_t_by_if[if_id] = mv_t
            fit_info[if_id] = {
                "integer_path": integer_path,
                "orig_index": orig_index,
                "outlier_mask": outlier_mask,
                "standardized_residual": fit.standardized_residual[::-1] if self.reverse else fit.standardized_residual,
            }
            # Store the Viterbi ambiguity path as automatic wrap adjustments so
            # plots and later manual edits use the same corrected data model.
            self.delay_auto_adjust_info.loc[orig_index, self._wrap_col(if_id)] = integer_path.astype(int)
            outlier_orig_index = orig_index[np.asarray(outlier_mask, dtype=bool)]
            if outlier_orig_index.size > 0:
                # Outliers identified during the solver refit are treated like
                # automatic flags for this IF.  Manual flags remain separate.
                self.delay_auto_adjust_info.loc[outlier_orig_index, self._flag_col(if_id)] = 1
            progress_current += 1
            report(f"IF {if_num}/{n_if}: done", progress_current, progress_total)

        report("Computing target correction", progress_total - 1, progress_total)
        self.delay_mv_result = delay_results
        self.delay_mv_t_by_if = delay_t_by_if
        self.delay_fit_info = fit_info
        first_if = next((if_id for if_id in self.delay_if_ids if delay_t_by_if.get(if_id, np.array([])).size > 0), None)
        self.delay_mv_t = delay_t_by_if[first_if] if first_if is not None else np.array([])
        self.delay_target_if = {}
        self._refresh_delay_target_series()
        report("Calculation complete", progress_total, progress_total)

    def delay_flag(self, timerange, calibrators, mode='flag'):
        return self.delay_flag_if(timerange, calibrators, 0, mode)

    def delay_flag_if(self, timerange, calibrators, if_id, mode='flag'):
        flag_index = (self.original_data['t'] >= timerange[0]) & (self.original_data['t'] <= timerange[1])
        calibrator_index = self.original_data['calsour'].isin(calibrators)
        criteria_index = flag_index & calibrator_index
        flag_col = self._flag_col(if_id)
        if flag_col not in self.delay_adjust_info.columns:
            return
        if mode == 'flag':
            self.delay_adjust_info.loc[criteria_index, flag_col] = 1
        elif mode == 'unflag':
            self.delay_adjust_info.loc[criteria_index, flag_col] = 0
        else:
            raise ValueError('available modes are: flag, unflag')
        self.update_delay_data(if_id)

    def delay_wrap(self, timerange, calibrators, if_id, mode='+', source='manual'):
        wrap_col = self._wrap_col(if_id)
        target_info = self.delay_adjust_info if source == 'manual' else self.delay_auto_adjust_info
        if wrap_col not in target_info.columns:
            return
        wrap_index = (self.original_data['t'] >= timerange[0]) & (self.original_data['t'] <= timerange[1])
        calibrator_index = self.original_data['calsour'].isin(calibrators)
        criteria_index = wrap_index & calibrator_index
        if mode == '+':
            target_info.loc[criteria_index, wrap_col] += 1
        elif mode == '-':
            target_info.loc[criteria_index, wrap_col] -= 1
        else:
            raise ValueError('available modes are: +, -')
        self.update_delay_data(if_id)

    def delay_apply_manual_to_all(self, if_id):
        src_flag_col = self._flag_col(if_id)
        src_wrap_col = self._wrap_col(if_id)
        if src_flag_col not in self.delay_adjust_info.columns or src_wrap_col not in self.delay_adjust_info.columns:
            return
        for other_if in self.delay_if_ids:
            self.delay_adjust_info[self._flag_col(other_if)] = self.delay_adjust_info[src_flag_col].to_numpy()
            self.delay_adjust_info[self._wrap_col(other_if)] = self.delay_adjust_info[src_wrap_col].to_numpy()
        self.update_delay_data(if_id)

    def delay_t_flag(self, timerange, mode='flag'):
        if mode == 'flag':
            range_to_append = timerange
            range_list = copy.deepcopy(self.delay_t_flag_info)
            loop_flag = True
            while loop_flag:
                loop_flag = False
                for item in range_list:
                    if item[0] < range_to_append[0] < range_to_append[1] < item[1]:
                        return
                    elif range_to_append[0] < item[0] < range_to_append[1] < item[1]:
                        range_to_append[1] = item[1]
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif item[0] < range_to_append[0] < item[1] < range_to_append[1]:
                        range_to_append[0] = item[0]
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_append[0] < item[0] < item[1] < range_to_append[1]:
                        range_list.remove(item)
                        loop_flag = True
                        break
            range_list.append(range_to_append)
            self.delay_t_flag_info = range_list
        elif mode == 'unflag':
            range_to_remove = timerange
            range_list = copy.deepcopy(self.delay_t_flag_info)
            loop_flag = True
            while loop_flag:
                loop_flag = False
                for item in range_list:
                    if item[0] < range_to_remove[0] < range_to_remove[1] < item[1]:
                        range_list.append([item[0], range_to_remove[0]])
                        range_list.append([range_to_remove[1], item[1]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_remove[0] < item[0] < range_to_remove[1] < item[1]:
                        range_list.append([range_to_remove[1], item[1]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif item[0] < range_to_remove[0] < item[1] < range_to_remove[1]:
                        range_list.append([item[0], range_to_remove[0]])
                        range_list.remove(item)
                        loop_flag = True
                        break
                    elif range_to_remove[0] < item[0] < item[1] < range_to_remove[1]:
                        range_list.remove(item)
                        loop_flag = True
                        break
            self.delay_t_flag_info = range_list
        else:
            raise ValueError('available modes are: flag, unflag')

    def delay_reset(self):
        self.delay_adjust_info.iloc[:, :] = 0
        self.delay_auto_adjust_info.iloc[:, :] = 0
        self.delay_t_flag_info = []
        self.update_delay_data(self.delay_if_ids[0] if self.delay_if_ids else 0)

    def delay_auto_reset(self):
        self.delay_auto_adjust_info.iloc[:, :] = 0
        self.update_delay_data(self.delay_if_ids[0] if self.delay_if_ids else 0)

    def plot_delay(self, target_pos, if_id=0, original_delay_id=None):
        self.target_pos = target_pos
        self.update_delay_data(if_id)
        self._refresh_delay_target_series()
        markers = ['o', 'd', '^', 's', 'v', 'p', 'h', '*', '8', '<', '>', 'H', 'D', 'X', 'P']
        fig, ax = plt.subplots(1, 1, figsize=(8, 3))
        fig.subplots_adjust(left=0.05, right=0.95, top=0.98, bottom=0.12)

        if if_id in self.delay_target_if and self.delay_target_if[if_id].size > 0:
            target_t = np.asarray(self.delay_mv_t_by_if.get(if_id, self.delay_mv_t), dtype=float)
            target_delay = np.asarray(self.delay_target_if[if_id], dtype=float)
            n_plot = min(target_t.size, target_delay.size)
            if n_plot > 0:
                ax.plot(target_t[:n_plot], target_delay[:n_plot] * 1e12, 'x', color='k', ls='', label='Target')

        for i, item in enumerate(self.secondary_calibrators):
            plot_data = self.data.copy(deep=True)
            plot_data = plot_data.loc[plot_data['calsour'] == item.id]
            plot_data = self._correct_delay_with_phase(plot_data, if_id)
            if not plot_data.empty:
                ax.plot(plot_data['t'], plot_data["total_delay"] * 1e12, ls='none', marker=markers[i], c=self.colors[i], label=item.name)

        flag_col = self._flag_col(if_id)
        flagged_index = self.delay_adjust_info[flag_col] == 1
        if flag_col in self.delay_auto_adjust_info.columns:
            flagged_index = flagged_index | (self.delay_auto_adjust_info[flag_col] == 1)
        flagged_data = self.original_data.loc[flagged_index].copy(deep=True)
        flagged_data.reset_index(drop=True, inplace=True)
        for i, item in enumerate(self.secondary_calibrators):
            plot_data = (flagged_data.copy(deep=True)).loc[flagged_data['calsour'] == item.id]
            plot_data = self._correct_delay_with_phase(plot_data, if_id)
            if not plot_data.empty:
                ax.plot(plot_data['t'], plot_data["total_delay"] * 1e12, ls='none', marker=markers[i], c=self.colors[i], alpha=0.3)

        # original delay
        if original_delay_id is not None:
            delay = self.original_data.loc[self.original_data['calsour'] == original_delay_id]
            if not delay.empty:
                ax.plot(delay['t'], delay[f"d{if_id}"] * 1e12, ls='-', marker=None, c="#888888", alpha=0.7, label=f"Ori. delay")

        ax.set_xlabel("time (day)")
        ax.set_ylabel("total delay (ps)")
        ax.set_title(f"IF{if_id + 1}")
        # ax.secondary_yaxis("right")
        scale = self.delay_scale.get(if_id)
        ax_r = ax.secondary_yaxis("right", functions=(lambda x: -x*scale/1e12, lambda x: -x/scale*1e12))
        ax_r.set_ylabel("corresponding phase (rad)", rotation=90)
        for item in self.delay_t_flag_info:
            y_lim = ax.get_ylim()
            ax.fill_betweenx(y_lim, item[0], item[1], color='#FFB6C1', alpha=0.15)
            ax.set_ylim(y_lim)
        ax.legend()
        return fig

    def save_delay(self, delay_adj_dir, delay_mv_dir):
        self._refresh_delay_target_series()
        self.delay_adjust_info.to_csv(delay_adj_dir, index=False)
        mv_table = pd.DataFrame({
            't': self.delay_average_t if self.delay_average_t is not None else [],
            'mbdelay': self.delay_average if self.delay_average is not None else [],
        })
        mv_table.to_csv(delay_mv_dir, index=False)
        # if self.delay_target_if:
        #     detail_path = delay_mv_dir.replace(".csv", "-IFS.csv")
        #     detail_table = pd.DataFrame({'t': self.delay_mv_t if self.delay_mv_t is not None else []})
        #     for if_id in self.delay_if_ids:
        #         if if_id in self.delay_target_if and self.delay_target_if[if_id].size > 0:
        #             detail_table[f'd{if_id}'] = self.delay_target_if[if_id]
        #     detail_table.to_csv(detail_path, index=False)

    def update_delay_data(self, if_id=0):
        self.update_delay_data_if(if_id)

    def update_delay_data_if(self, if_id):
        self.data = self.original_data.copy(deep=True)
        if self.data.empty:
            return
        self.data["_orig_index"] = self.data.index
        flag_col = self._flag_col(if_id)
        wrap_col = self._wrap_col(if_id)
        if flag_col not in self.delay_adjust_info.columns or wrap_col not in self.delay_adjust_info.columns:
            return
        combined_adjust = pd.DataFrame(index=self.delay_adjust_info.index)
        combined_adjust[flag_col] = self.delay_adjust_info[flag_col].astype(int)
        combined_adjust[wrap_col] = self.delay_adjust_info[wrap_col].astype(int)
        if not self.delay_auto_adjust_info.empty:
            if flag_col in self.delay_auto_adjust_info.columns:
                combined_adjust[flag_col] = combined_adjust[flag_col] + self.delay_auto_adjust_info[flag_col].fillna(0).astype(int)
            if wrap_col in self.delay_auto_adjust_info.columns:
                combined_adjust[wrap_col] = combined_adjust[wrap_col] + self.delay_auto_adjust_info[wrap_col].fillna(0).astype(int)
        # for if_id in self.delay_if_ids:
        #     phase_col = f'p{if_id}'
        #     delay_col = f'd{if_id}'
        #     if phase_col in self.data.columns and delay_col in self.data.columns:
        #         freq_hz = self.if_freq.get(if_id, 1.0) * 1e9
        #         self.data[delay_col] = self.data[delay_col] - self.data[phase_col] / (2 * np.pi * freq_hz)
        delay_col = f'd{if_id}'
        if delay_col in self.data.columns:
            wrap_step = 1.0 / (self.if_freq.get(if_id, 1.0) * 1e9)
            self.data[delay_col] += combined_adjust[wrap_col].to_numpy() * wrap_step
        non_flagged_index = combined_adjust[flag_col] == 0
        self.data = self.data.loc[non_flagged_index]
        self.data.reset_index(drop=True, inplace=True)

    def plot_delay_normal_vector(self, if_id=None):
        """Plot the fitted mapped-elevation/AltAz delay gradients.

        The historical method name is retained because several GUI classes call
        it, but the plotted quantity is no longer a 3D normal vector.
        """
        if if_id is None:
            if_id = self.delay_if_ids[0] if self.delay_if_ids else 0
        if if_id not in self.delay_mv_result:
            return plt.figure(figsize=(8, 4))
        mv_t = self.delay_mv_t_by_if.get(if_id, self.delay_mv_t)
        if mv_t is None or len(mv_t) == 0:
            return plt.figure(figsize=(8, 4))
        fig, ax = plt.subplots(1, 1, figsize=(5.0, 3.6))
        fig.subplots_adjust(left=0.24, right=0.96, top=0.88, bottom=0.20)
        mv = self.delay_mv_result[if_id]
        n_plot = min(len(mv_t), len(mv))
        mv_t = np.asarray(mv_t, dtype=float)[:n_plot]
        mv = mv[:n_plot]
        grad_labels = [elevation_coordinate_label(self.elevation_mapping), "azimuth"]
        for i in range(min(2, mv.shape[1])):
            ax.plot(mv_t, mv[:, i] * 1e12, ls=['-', '--'][i], label=grad_labels[i])
        ax.set_xlabel("time (day)")
        ax.set_ylabel(gradient_axis_label(self.elevation_mapping))
        ax.legend()
        ax.set_title(f"Mapped AltAz Delay Gradients (IF{if_id + 1})")
        return fig

    def _refresh_delay_target_series(self):
        """Evaluate fitted gradients at the target position and average IFs."""
        if not isinstance(self.delay_mv_result, dict):
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
            return
        refreshed = {}
        for if_id, mv_res in self.delay_mv_result.items():
            times_raw = self.delay_mv_t_by_if.get(if_id, self.delay_mv_t)
            if mv_res.size == 0 or times_raw is None or len(times_raw) == 0 or self.target is None:
                refreshed[if_id] = np.array([])
                continue
            times = np.asarray(times_raw, dtype=float)
            n_target = min(len(times), len(mv_res))
            target_offsets = self.source_altaz_offsets(self.target, times[:n_target], self.elevation_mapping)
            refreshed[if_id] = np.sum(mv_res[:n_target, :2] * target_offsets, axis=1)
        self.delay_target_if = refreshed
        valid_items = [(if_id, arr) for if_id, arr in self.delay_target_if.items() if arr.size > 0]
        if valid_items:
            base_if, base_arr = valid_items[0]
            base_t = np.asarray(self.delay_mv_t_by_if.get(base_if, self.delay_mv_t), dtype=float)
            aligned = [base_arr]
            for if_id, arr in valid_items[1:]:
                this_t = np.asarray(self.delay_mv_t_by_if.get(if_id, self.delay_mv_t), dtype=float)
                if arr.size == base_arr.size and np.allclose(this_t, base_t):
                    aligned.append(arr)
                else:
                    aligned.append(np.interp(base_t, this_t, arr))
            self.delay_average = np.mean(np.vstack(aligned), axis=0)
            self.delay_average_t = base_t
        else:
            self.delay_average = np.array([])
            self.delay_average_t = np.array([])
    
    def _correct_delay_with_phase(self, data_in, if_id):
        """Build a phase-consistent total-delay observable for one IF.

        The SN delay remains in seconds.  ``delay_scale`` converts between delay
        and phase at the IF frequency so that the exported phase residual can
        choose the phase-consistent delay branch before ambiguity search.
        """
        scale = self.delay_scale.get(if_id, 1.0)
        phase_of_delay = (-data_in[f"d{if_id}"] * scale + np.pi) % (2 * np.pi) - np.pi
        delta_phase = data_in[f"p{if_id}"] - phase_of_delay
        data_in["total_delay"] = data_in[f"d{if_id}"] - delta_phase / scale
        return data_in
