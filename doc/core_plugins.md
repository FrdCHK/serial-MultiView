# Core Plugins

This document lists the built‑in plugins by category. Each plugin is a class derived from `core.Plugin`.

## Core framework
- `AipsCatalog`: tracks AIPS catalogs and extension tables (SN/CL).
- `GetObsInfo`: reads antennas, sources, and observation metadata.
- `Exit`: pipeline terminator.

## AIPS task wrappers (`plugin/core/aips_task`)
These are thin wrappers around AIPSTask. All log start/end and register SN/CL tables in `AipsCatalog` when relevant.
- `AipsInit`: AIPS user/session setup.
- `Fitld`: load FITS to AIPS.
- `Accor`, `Apcal`: amplitude calibration.
- `Clcal`: apply SN to CL.
- `Clcor`: apply corrections (PANG/EOPS).
- `Fring`: fringe fitting.
- `Tecor`: ionosphere correction.
- `Imagr`: imaging.
- `GeneralTask`: generic wrapper for any AIPS task (POSSM, SPLIT, FITTP, JMFIT, UVFLG, LISTR, PRTAN, etc.).

## External files
- `Eop`: download/locate EOP files.
- `Ionex`: download/locate ionosphere files.

## Antenna management
- `RefAntSelect`: auto/manual reference antenna selection.

## Source management
- `PRSourceSelect`: pick targets and calibrators, create SPLAT catalogs.
- `MVPrimaryCalibratorSelect`: choose primary calibrator for MV.
- `SelfcalSourceSelect`: select targets for self‑cal.

## PR workflow
- `PRCalibratorFringeFitting`: fringe fit calibrators and generate CL tables.
- `PRCalibratorFitsExport`: SPLIT + FITTP of calibrators.
- `PRCalibratorMapping`: difmap mapping for calibrators.
- `PRCalibratorStructureCorrection`: apply structure correction.
- `PRTargetMapping`: PR target imaging and optional JMFIT.

## MV workflow
- `MVPrimaryFringeFitting`: FRING primary calibrator and apply to all sources.
- `MVSecondaryFringeFitting`: FRING secondary calibrators only.
- `MVSnExport`: export SN tables for MV.
- `MVRun`: MultiView GUI workflow.
- `MVPostProcess`: import MV SN, SPLIT/UVFLG/IMAGR/JMFIT/FITTP, summary.

## Self‑cal workflow
- `SelfcalFringeFitting`: fringe fit targets for self‑cal.
- `SelfcalFitsExport`: SPLIT + FITTP for targets.
- `SelfcalMapping`: difmap mapping for targets.

## IO and difmap
- `FitsExport`: helper class for SPLIT + FITTP.
- `Difmap`: calls difmap mapping scripts.
