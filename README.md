# Python scripts for MultiView
**Developed by Jingdong Zhang, Shanghai Astronomical Observatory & Finnish Geospatial Research Institute, June 2024**

## NOTE: This version is under development. For the version which works for the standard VLBA MultiView workflow, please refer to the legacy branch.

## Brief introduction
Conventional Phase-referencing may introduce small phase bias due to the angular separation between target and calibrator. MultiView technique (Rioja et al., 2017) can improve VLBI relative measurement calibration through estimating a "phase plane" with several calibrators surrounding a target source. The scripts here provide a semi-automatic and easy-to-use workflow for serial MultiView phase plane estimation. The most tricky problem for MultiView, **2$\pi$-ambiguity, is automatically detected and solved** through an iteration/recursion procedure. The design of the observation schedule does not need to strictly follow the cyclic pattern proposed by Rioja et al. (cycling observing target and all calibrators), which **allows more frequent observation of the main calibrator and target**. For more details, please read our paper: [Zhang et al. 2025](https://iopscience.iop.org/article/10.3847/1538-3881/add40e).

## Observation and data
* The observation should be designed in MultiView mode:
    + 1 target;
    + 3 or more calibrators surrounding the target, at least one among them should be bright and has an accurate a priori position;
    + Observe the target and calibrators alternately.

_It is OK to have only 2 calibrators, but make sure C1-T-C2 are approximately aligned in a straight line._
_You don't need to strictly observe the sources in a conventional C1-C2-T-C3-C4-... MultiView cycle. For example, you can observe the primary calibrator and target more frequently for better coherence and longer on-source time: C1-T-C2-C1-T-C3-C1-T-C4-..._
