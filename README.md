# Python scripts for MultiView (VLBA obs.)
**Developed by Jingdong Zhang, Shanghai Astronomical Observatory, June 2024**

## Brief introduction
Conventional Phase-referencing may introduce small phase bias due to the angular separation between target and calibrator. MultiView technique (Rioja et al., 2017) can improve VLBI relative measurement calibration through estimating a "phase plane" with several calibrators surrounding a target source. The scripts here provide a semi-automatic and easy-to-use workflow for serial-MultiView phase plane estimation. The most tricky problem for MultiView, **2$\pi$-ambiguity, is automatically detected and solved** through an iteration/recursion procedure. The design of the observation schedule does not need to strictly follow the cyclic pattern proposed by Rioja et al. (cycling observing target and all calibrators), which **allows more frequent observation of the main calibrator and target**. For more details, please read our paper: Zhang et al., _in prep._

## Observation and data
* The observation should be designed in MultiView mode:
    + 1 target;
    + 3 or more calibrators surrounding the target, at least one among them should be bright and has an accurate a priori position;
    + Observe the target and calibrators alternately.

_It is OK to have only 2 calibrators, but make sure C1-T-C2 are approximately aligned in a straight line._
_You don't need to strictly observe the sources in a conventional C1-C2-T-C3-C4-... MultiView cycle. For example, you can observe the primary calibrator and target more frequently for better coherence and longer on-source time: C1-T-C2-C1-T-C3-C1-T-C4-..._

## How to use the scripts

### Environment
* Although Python is cross-platform, AIPS and ParselTongue may not work perfectly on some platforms, so Linux is recommended (tested on CentOS 7);
* Make sure you have correctly installed AIPS and ParselTongue 3;
* The scripts have been tested under Python 3.9;
* Python packages required:
    * Numpy
    * Pandas
	* Scipy
    * Matplotlib
    * Astropy
    * pyyaml
    * pycurl

### Edit config.yaml
Configurations for the scripts. See the comments for each parameter in the example yaml file for details.

### Run the pre-process script
* Run script _**pre-process.py**_ with ParselTongue:
    ```
    ParselTongue pre-process.py
    ```

* The script will automatically load the data and run some calibration tasks. If there are multiple data files, please rename them to the format of _\<name\>.1, \<name\>.2, ..._ and input _\<name\>.1_ in the config file.
* EOP and ionex files will be automatically downloaded. Please make sure that you have internet connection.

* Calibrator selection:
    * You can select primary and secondary calibrators for each target in the procedure. Task POSSM can be run in an AIPSTV window (optional).
    * For muiti-epoch observations, you can save the calibrator list and load it for other epochs.

* Position offset:
    * The offset of the target phase centre is determined by repeatedly running task IMAGR. You can adjust the IMAGR parameters during this process and determine the offset automatically or manually.

### Run the MultiView script
* Run script _**multiview.py**_:
    ```
    python multiview.py
    ```

* There will be three GUI windows: "PLOT", "CONFIG", and "ADJUST".
    * "PLOT" window will show an image of the variation of the normal vector of phase plane. The "rerun" button will run MultiView again with adjusted parameters/data. The "finish" button will save the results and adjustments you've made to ./exp/\<expname-userid\>/. If you run the script again, the adjustments will be automatically loaded.
    * The MultiView procedure will be run with default parameters set in the config file, but you can adjust serial-MultiView parameters in "CONFIG" window. Please remember to press "save" button to save the changes.
    * "ADJUST" window allows you to flag or wrap some of the data points. First, press "manual adjustment" button to switch to edit mode. The image will become interactive: left click with mouse to set the start of a time range, then right click to set the end. Select the calibrator(s) you want to edit in this time range, then press one of "+2$\pi$", "-2$\pi$", "flag", and "unflag" buttons. Remember to press "rerun" button in "PLOT" window to apply the changes.
* Screen resolution $\ge$1920*1080 is recommended for the GUI. A width of 1320 is the minimum requirement.
* When you run _**multiview.py**_ for the first time, MultiView will be run for all antennas of all targets. If you run it again, you can choose to run all of them again or select specific ones to run.

### Run the post-process script
* Run script _**post-process.py**_ with ParselTongue:
    ```
    ParselTongue post-process.py
    ```

* This script will run several tasks to apply MultiView SN tables to the data and export the images and JMFIT results to files. You can find the fits images, JMFIT exported files, and JMFIT summary csv files in ./exp/\<expname-userid\>/. The results of conventional phase-referencing will also be exported.
* If you want to redo the post-processing procedure, please run script _**post-process-reset.py**_:
    ```
    python post-process-reset.py
    ```
  Then manually run RESET in AIPS (because ParselTongue does not support AIPS verbs), see comments in _**./run/RESET.001**_ generated by _**post-process.py**_.

### Notes
* If the calibration or imaging parameters used in the scripts do not match your needs, feel free to edit the scripts or do it manually in AIPS.

#### Coming soon ...
* Add support to other VLBI networks.
* Add support to Inverse MultiView.
