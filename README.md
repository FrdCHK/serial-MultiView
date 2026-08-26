# Python scripts for MultiView

**Developed by Jingdong Zhang, Shanghai Astronomical Observatory & Finnish Geospatial Research Institute, June 2024**

## Note

This repo is under active development. For fewer bugs, use the stable released version.

## What this repo is

A modular VLBI pipeline framework with a focus on serial MultiView (sMV) phase plane estimation. The current delay-MV implementation fits station-local mapped-elevation/AltAz delay gradients with a Viterbi-Kalman/RTS solver, optional cosecant elevation mapping, and optional separation-dependent weighting. Independent IFs can run in parallel, while the time-dependent Viterbi, Kalman, and RTS steps within each IF remain sequential. The core idea is:

- Calibrate and prepare data with AIPS/ParselTongue tasks.
- Use MultiView to estimate a phase plane from multiple calibrators.
- Apply the MultiView solution and produce PR/MV images and statistics.

## Repository structure

- `core/`: framework core (context, plugin base, logger, plugin loader)
- `plugin/`: all pipeline functionality
  - `plugin/core/`: built-in plugins (AIPS tasks, calibration flow, MV, PR, self-cal)
  - `plugin/core/mv/`: MultiView core plugins and GUI helpers
  - `plugin/custom/`: your custom plugins
- `template/`: Jinja2 control file templates (pipelines)
- `config/`: example configuration
- `util/`: shared helpers (inputs, parsing, map center, summary, etc.)
- `doc/`: detailed documentation
- `tests/`: solver, control-rendering, progress-state, and GUI-coordination regression tests

## Quickstart

1. Create a conda environment:

   - Use `environment.yaml`.

2. Edit the config file:

   - Start with `config/config.yaml` and set your paths and parameters.
   - Use `''` for empty strings (for example `uvwtfn`).

3. Generate a control file from a template:

   - `python gen_control_file.py --template template/vlba_smv.yaml.j2 --config config/config.yaml --control /path/to/control.yaml`

4. Run the pipeline:

   - `ParselTongue main.py --control /path/to/control.yaml --log log`
   - Make sure AIPS and ParselTongue are installed, and the environment variables are set.

## Templates (pipelines)

- `template/manual_smv.yaml.j2`: run sMV from manually prepared AIPS/SN data
- `template/vlba_pr.yaml.j2`: standard single-calibrator PR
- `template/vlba_pr_calsour_struc.yaml.j2`: PR with calibrator self-cal and structure correction
- `template/vlba_selfcal_mapping.yaml.j2`: self-cal mapping workflow
- `template/vlba_smv.yaml.j2`: serial MultiView workflow (sMV)
- `template/vlba_smv_calsour_struc.yaml.j2`: serial MultiView with calibrator structure correction

Each template expands a `config:` section and a sequential `plugins:` list. The order in the list is the pipeline order.

## MultiView solver configuration

The public delay-solver settings are in `config/config.yaml`, in every sMV template, and in the MV config window. `parallel_workers: 0` automatically uses up to one worker process per valid IF, bounded by the detected CPU count. A positive integer sets a smaller cap; negative and non-integer values are rejected.

The modal calculation window reports aggregate and per-IF status while the solver coordinator runs outside the Tk main thread. Results are committed only after all valid IFs and final averaging succeed, so a failed IF does not replace the previous solution with partial output.

Old configurations using `viterbi_integer_states`, `viterbi_max_jump`, `viterbi_jump_penalty`, `viterbi_huber_c`, or `viterbi_z_out` are migrated to the current names when a control file or saved MV configuration is loaded. If both spellings contain values, the current name takes precedence. See `doc/mv_viterbi_kalman_altaz.md` for the model, defaults, GUI behavior, and full compatibility mapping.

## Where outputs go

By default, outputs are written under `config.workspace`:

- Results for each target: `workspace/targets/<target>/...`

## Tests

Run the tracked Python 3.8/ParselTongue regression suite from the repository root:

```bash
ParselTongue -m pytest -q tests
```

The Tk integration test skips when no display is available. Run it under a native display or Xvfb for GUI validation; representative AIPS data are still required for an end-to-end pipeline smoke test.

## AIPS task references

If you want more details about AIPS tasks, use the NRAO help pages:

- https://www.aips.nrao.edu/cgi-bin/ZXHLP2.PL?FRING
- Replace `FRING` with the task name.

## Documentation

- `doc/framework.md`: pipeline framework overview
- `doc/custom_plugin.md`: how to develop custom plugins
- `doc/core_plugins.md`: core plugin catalog (by category)
- `doc/mv_viterbi_kalman_altaz.md`: current sMV mapped-elevation/AltAz Viterbi-Kalman delay model and implementation notes
