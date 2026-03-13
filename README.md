# Python scripts for MultiView
**Developed by Jingdong Zhang, Shanghai Astronomical Observatory & Finnish Geospatial Research Institute, June 2024**

## Note
This repo is under active development. For a stable legacy workflow, use the legacy branch of the original repo.

## What this repo is
A modular VLBI pipeline framework with a focus on serial MultiView (sMV) phase plane estimation. The core idea is:
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
- `template/vlba_pr.yaml.j2`: standard single-calibrator PR
- `template/vlba_pr_calsour_struc.yaml.j2`: PR with calibrator self-cal and structure correction
- `template/vlba_selfcal_mapping.yaml.j2`: self-cal mapping workflow
- `template/vlba_smv.yaml.j2`: serial MultiView workflow (sMV)

Each template expands a `config:` section and a sequential `plugins:` list. The order in the list is the pipeline order.

## Where outputs go
By default, outputs are written under `config.workspace`:
- Results for each target: `workspace/targets/<target>/...`

## AIPS task references
If you want more details about AIPS tasks, use the NRAO help pages:
- https://www.aips.nrao.edu/cgi-bin/ZXHLP2.PL?FRING
- Replace `FRING` with the task name.

## Documentation
- `doc/framework.md`: pipeline framework overview
- `doc/custom_plugin.md`: how to develop custom plugins
- `doc/core_plugins.md`: core plugin catalog (by category)
