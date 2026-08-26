# Mapped-Elevation AltAz Viterbi-Kalman MultiView

This document describes the current serial MultiView workflow in
`plugin/core/mv`. Here, serial MultiView names the observing/analysis method;
independent IF solutions can execute concurrently. The implementation replaces
the older recursive normal-vector solver with per-IF Viterbi-Kalman solvers in
station-local mapped-elevation/AltAz coordinates.

## Scope

The solver is used by `MVRun` after `MVSnExport` has written one SN CSV per
secondary calibrator.  It operates per target and per antenna in the GUI.  For
each IF it estimates an atmospheric delay-gradient time series, evaluates that
gradient at the target position, and saves the averaged target correction as:

```text
t, mbdelay
```

That output format is intentionally unchanged so `MVPostProcess` can continue
importing MV corrections.

## Coordinate Model

The primary calibrator is the zero point of the delay plane.  For every scan and
every station, source coordinates are converted from ICRS RA/DEC to AltAz with
Astropy:

```python
EarthLocation.from_geocentric(X, Y, Z)
Time(obs_jd0 + t, format="jd", scale="utc")
AltAz(obstime=..., location=...)
```

The solver coordinates are primary-relative.  The azimuth coordinate is always:

```text
delta_az = wrap_at_180(secondary_az - primary_az)
```

The elevation coordinate is selected by `elevation_mapping`:

```text
linear:   x_el = secondary_alt - primary_alt
cosecant: x_el = 1/sin(secondary_alt) - 1/sin(primary_alt)
```

For `linear`, `x_el` and `delta_az` are both in degrees.  For `cosecant`,
`x_el` is a raw dimensionless slant-mapping difference while `delta_az` remains
in degrees.  Any invalid mapping name read from config is treated as `linear`.
The same mapping is used for the target when the final target correction is
evaluated.  Because AltAz coordinates change with Earth rotation, offsets are
recomputed for each scan time, not cached as one static sky-plane separation.

## Delay Observable

For each IF, `Antenna._correct_delay_with_phase` builds a phase-consistent total
delay in seconds.  The exported delay column remains the delay observable; the
exported phase is used only to select the phase-consistent branch before the
ambiguity search.

The base observation variance is set by the SN weight.  An optional
separation-dependent noise term can be added to reduce the leverage of distant
secondary calibrators:

```text
theta_i = sqrt(delta_el_linear_i^2 + delta_az_i^2)
R_i = unit_weight_variance * (1 / SN_weight_i + (separation_noise * theta_i)^2)
```

`theta_i` is always the true linear angular separation in degrees, even when
`elevation_mapping = cosecant`.  `separation_noise` is a dimensionless tuning
coefficient relative to `unit_weight_variance`; `0.0` disables this term and
recovers the previous `unit_weight_variance / SN_weight_i` behavior.  Positive
values make distant secondary calibrators less able to dominate the gradient
fit or force the Viterbi ambiguity path, while close calibrators retain their
SN-weight-driven influence.

Rows with missing values, non-finite offsets, or non-positive weights are
skipped.  `unit_weight_variance` is fixed internally because the current output
does not use absolute posterior variances; relative SN weights and relative
separation penalties are what matter.

The delay ambiguity spacing for IF `k` is:

```text
ambiguity_spacing_k = 1 / if_freq_hz_k
```

## Continuous State Model

The fitted delay plane passes through the primary calibrator, so there is no
intercept or center-delay state.  The continuous state is:

```text
x_i = [g_el_i, g_az_i, dg_el_dt_i, dg_az_dt_i]^T
```

For `linear`, `g_el` and `g_az` have units of seconds per degree.  For
`cosecant`, `g_el` has units of seconds per cosecant-unit while `g_az` remains
seconds per degree.  The two rate terms are temporal derivatives of those
gradients per day.  They are estimated from the delay time series by the Kalman
dynamics.  The SN rate columns are not used as solver input.

For a secondary calibrator observation:

```text
y_i + n_i * ambiguity_spacing = H_i x_i + e_i
H_i = [x_el_i, delta_az_i, 0, 0]
e_i ~ N(0, R_i)
```

`n_i` is the integer phase ambiguity for the secondary calibrator observed at
row `i`.

The state transition for time step `dt` in days is:

```text
F(dt) =
[1 0 dt 0 ]
[0 1 0  dt]
[0 0 1  0 ]
[0 0 0  1 ]
```

The process noise is a local-linear random-walk model.  With
`q = kalman_factor`, each gradient axis uses:

```text
Q_axis(dt) = q * [abs(dt)^3 / 3   abs(dt)^2 / 2]
                 [abs(dt)^2 / 2   abs(dt)      ]
```

This 2x2 block is placed on the elevation-gradient/rate and
azimuth-gradient/rate subspaces.  Larger `kalman_factor` allows the fitted
gradients to change faster in time.

## Viterbi Ambiguity Model

The ambiguity integer is persistent per secondary calibrator.  The Viterbi
state is a tuple:

```text
(N_cal1, N_cal2, ..., N_calM)
```

At an observation, only the integer of the currently observed calibrator may
change.  `max_jump` limits the allowed change between adjacent observations of
that calibrator, and `jump_penalty` adds cost when a change occurs.

For each candidate integer, the solver performs a scalar Kalman update and adds
an observation cost:

```text
cost_obs = Huber(z_i; huber_c) + log(S_i)
z_i = innovation_i / sqrt(S_i)
S_i = H_i P_pred H_i^T + R_i
```

The Huber cost is quadratic for small standardized residuals and linear for
large residuals.  Robust fitting is currently fixed on.  After the last row, the
lowest-cost branch is backtracked to recover the integer path.

`integer_states` is exposed as a single radius `n` in config and the GUI.  It is
expanded internally to:

```text
[-n, ..., 0, ..., n]
```

The adjust window can optionally fix initial ambiguity integers independently
for each secondary calibrator.  If the checkbox is off, all initial integers are
zero.

## Outliers and RTS Smoothing

After an integer path is selected, the solver runs a final Kalman fit on the
ambiguity-corrected delay series.  It then identifies outliers using:

```text
abs(standardized_residual) > z_out
```

The Viterbi search and Kalman fit are repeated after removing newly identified
outliers, up to the internally fixed iteration limit.  Outliers are written into
`Antenna.delay_auto_adjust_info` as automatic per-IF flags, so plots and later
manual edits see the same corrected data model.

If `rts_smoothing` is enabled, the forward Kalman states are followed by a
Rauch-Tung-Striebel backward pass.  This uses future scans to smooth the
gradient and gradient-rate time series.  Disabling it leaves the forward-filtered
state sequence.

## Parallel IF Execution

IFs do not share an ambiguity path or Kalman state, so valid IF inputs are sent
to separate spawn-based worker processes.  The observation sequence inside one
IF remains serial because Viterbi transitions, forward filtering, and RTS
smoothing depend on adjacent times.  Station/source AltAz coordinates are
prepared once and reused while building the IF-specific observables.

The worker limit is controlled by `parallel_workers`. `0` selects
`min(valid_IF_count, os.cpu_count() or 1)`; a positive value is an explicit cap
bounded by the valid IF count. Negative and non-integer values are rejected. A
single effective worker runs inline without process-start overhead. Empty IFs
are skipped normally.

Each worker returns arrays without modifying `Antenna`.  Automatic wraps,
outlier flags, per-IF fits, target corrections, and the averaged delay are
committed only after every worker and final aggregation succeed.  A failed IF
therefore leaves the previously committed solution intact, and dictionary/CSV
ordering continues to follow the configured IF order rather than completion
order.

## Public Parameters

These keys appear in `config/config.yaml`, the sMV templates, and the GUI config
window:

- `kalman_factor`: process-noise scale `q` for gradient/rate evolution; default
  `1.0e-14`.
- `rts_smoothing`: enable the RTS backward smoother after the forward Kalman
  pass; default `true`.
- `elevation_mapping`: `linear` or `cosecant`; invalid strings fall back to
  `linear`, which is also the default.
- `separation_noise`: unitless angular-separation noise coefficient; default
  `0.0` preserves the old SN-weight-only variance.
- `parallel_workers`: simultaneous IF solver processes; `0` uses the automatic
  CPU-aware limit and positive integers set an explicit cap.
- `integer_states`: integer search radius `n`, expanded to `[-n, ..., n]`;
  default `3`.
- `max_jump`: maximum ambiguity-integer change allowed for one calibrator step;
  default `1`.
- `jump_penalty`: fixed Viterbi cost added when an ambiguity integer changes;
  default `25.0`.
- `huber_c`: Huber threshold in standardized-residual units; default `3.0`.
- `z_out`: automatic outlier threshold in standardized-residual units; default
  `4.0`.

These controls are fixed in `plugin/core/mv/solver_config.py`:

- `unit_weight_variance = 4e-22`
- robust Viterbi cost enabled
- maximum outlier-refit iterations
- automatic initial covariance scale

Older input and saved configs containing `viterbi_*` keys are migrated to the
current public names before control rendering and when loaded. The mappings are
`viterbi_integer_states` to `integer_states`, `viterbi_max_jump` to `max_jump`,
`viterbi_jump_penalty` to `jump_penalty`, `viterbi_huber_c` to `huber_c`, and
`viterbi_z_out` to `z_out`; the legacy initial-ambiguity keys are migrated in
the same way. A populated current key wins over its legacy alias.

## Algorithm Schematics

- [Compact control-flow overview](viterbi_kalman_rts_overview.pdf) for one IF.
- [Implementation-level flow](viterbi_kalman_rts_detailed.pdf) for the Viterbi,
  Kalman, outlier-refit, and RTS calculation within one IF.

## Implementation Map

- `plugin/core/mv/viterbi_kalman_altaz.py`: numerical solver and AltAz offset
  helper.
- `plugin/core/mv/elevation_mapping.py`: elevation mapping choices,
  normalization, coordinate transform, and plot labels.
- `plugin/core/mv/solver_config.py`: public defaults, legacy key migration, and
  GUI-to-solver keyword translation.
- `plugin/core/mv/Antenna.py`: per-IF data preparation, phase-consistent delay
  construction, atomic result assembly, target correction evaluation, and CSV
  export.
- `plugin/core/mv/delay_parallel.py`: picklable IF payload/result types, worker
  count policy, spawn-based scheduling, and the pure per-IF solver call.
- `plugin/core/mv/MVRun.py`: collects SN exports, station X/Y/Z, observation JD,
  primary/target metadata, and creates one `Antenna` GUI session per antenna.
- `plugin/core/mv/Gui.py`: creates the root, config, and adjust windows; first
  solve and rerun both go through `RootWindow.rerun`.
- `plugin/core/mv/RootWindow.py`: owns saved paths, the compact AltAz-gradient
  plot, the rerun button, and the progress popup.
- `plugin/core/mv/AdjustWindow.py`: manual flags/wraps, IF selection, time flags,
  initial ambiguity editor, and delay plot.
- `plugin/core/mv/Slice3DWindow.py`: 3D time-slice visualization of the
  primary-anchored mapped-elevation/AltAz delay plane.
- `plugin/core/mv/ProgressWindow.py`: modal progress dialog for initial solve
  and rerun.

## GUI Behavior

The config window stages solver parameter edits.  Saving or resetting parameters
does not automatically rerun the solver.  Manual flagging, wrapping, reset,
`all IFs`, and initial-ambiguity controls also update the displayed data without
launching a solve.  Press `rerun` in the root window when you want the current
edits and parameters to be used.

During first run and rerun, the modal, non-cancellable progress dialog shows one
status row per IF plus an aggregate completed-IF bar. IFs can move through
queued, preparing, running, complete, skipped, failed, or cancelled states in
any order. A coordinator thread sends structured events through a thread-safe
queue, and `root.after(...)` drains that queue on the Tk main thread. Worker
processes and the coordinator never call Tk. After all valid IFs complete, the
dialog reports target-correction combination and closes automatically. On
failure it closes, reports the failing IF, and does not refresh plots from
partial results.

The 3D slice window visualizes the fitted plane at the selected time range as
`delay = grad_el * x_el + grad_az * delta_az`.  X and Y keep their independent
numeric data limits, but their visual axis lengths are forced equal so cosecant
elevation and azimuth degrees remain readable on the same plot.  Right-drag
continues to adjust only the Z aspect.

## Saved Files

For each target and antenna, the GUI saves:

- manual delay adjustments: `*-DELAY-ADJ.csv`
- per-antenna config: `*-CONF.yaml`
- averaged target delay correction: `*-DELAY.csv` with `t, mbdelay`
- diagnostic plots for the delay data and mapped-elevation/AltAz delay gradients

Automatic Viterbi wraps and outlier flags are not persisted as manual edits;
they are recomputed on rerun from the saved parameters and manual edits.
