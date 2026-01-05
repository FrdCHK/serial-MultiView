from typing import Dict, Tuple
import os
from jinja2 import Environment, FileSystemLoader
import subprocess
import re
import numpy as np
from astropy.io import fits
from scipy.ndimage import label

from core.Plugin import Plugin
from core.Context import Context


class Difmap(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Call difmap to clean and self calibrate the calibrator maps. Difmap must be installed and can be called through command 'difmap'."
    
    def run(self, context: Context) -> bool:
        # TODO : add adjustable parameters from config & progress log info
        context.logger.info(f"Start calibrator self-calibration with Difmap")

        env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))), trim_blocks=True, keep_trailing_newline=True)

        shallow_template = env.get_template("shallow_clean.par.j2")
        deep_template = env.get_template("deep_clean.par.j2")
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        try:
            # pgplot cannot accept long path, so create a temp link to the targets directory
            pg_link = "pg_link"
            if not os.path.exists(pg_link):
                os.symlink(targets_dir, pg_link)
            elif os.path.exists(pg_link) and (not os.path.islink(pg_link)):
                context.logger.error(f"Failed to create symlink for PGPLOT: {pg_link} already exists and is not a symlink")
                return False
            for target in context.get_context().get("targets"):
                target_dir = os.path.join(pg_link, target["NAME"])
                calibrators_dir = os.path.join(target_dir, "calibrators")
                for calibrator in target["CALIBRATORS"]:
                    # shallow clean
                    config = {"uv_file": os.path.join(calibrators_dir, f"{calibrator['NAME']}_FITTP.fits"),
                              "IF_end": context.get_context()["no_if"],
                              "save_file_prefix": os.path.join(calibrators_dir, f"{calibrator['NAME']}_shallow"),
                              "field_cell": 2/context.get_context()["obs_freq"]}  # the cell size is based on typical VLBA value
                    par = shallow_template.render(**config)
                    par_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "difmap_commands.par")
                    with open(par_path, 'w') as file:
                        file.write(par)
                    imstat = self.run_difmap(par_path)
                    os.remove(par_path)
                    # determine the field size
                    field_size, _ = self.auto_fov_shrink(context, os.path.join(calibrators_dir, f"{calibrator['NAME']}_shallow.fits"), imstat["rms"])
                    for filename in os.listdir(calibrators_dir):
                        if filename.startswith(f"{calibrator['NAME']}_shallow"):
                            os.remove(os.path.join(calibrators_dir, filename))
                    # deep clean
                    config = {"uv_file": os.path.join(calibrators_dir, f"{calibrator['NAME']}_FITTP.fits"),
                              "IF_end": context.get_context()["no_if"],
                              "save_file_prefix": os.path.join(calibrators_dir, f"{calibrator['NAME']}_selfcal"),
                              "field_size": field_size*2,
                              "field_cell": imstat["bmin"]/5}  # Difmap halves the actual field size due to algorithm issue
                    par = deep_template.render(**config)
                    par_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "difmap_commands.par")
                    with open(par_path, 'w') as file:
                        file.write(par)
                    imstat = self.run_difmap(par_path)
                    os.remove(par_path)
        except Exception as e:
            context.logger.info(f"Error in calibrator self-calibration: {e}")
            return False
        finally:
            if os.path.islink(pg_link):
                os.remove(pg_link)
            for filename in os.listdir(os.getcwd()):
                if filename.startswith("difmap.log"):
                    os.remove(os.path.join(os.getcwd(), filename))

        context.logger.info(f"Calibrator self-calibration finished")
        return True

    @staticmethod
    def run_difmap(par_path: str) -> Dict:
        process = subprocess.run(["difmap"],
                                 stdin=open(par_path),
                                 # stdout=subprocess.DEVNULL,
                                 # stderr=subprocess.DEVNULL,
                                 text=True,
                                 capture_output=True,
                                 check=True)
        rms = float(re.search(r"imstat rms\s*=\s*([0-9.eE+-]+)", process.stdout).group(1))
        bmin = float(re.search(r"imstat bmin\s*=\s*([0-9.eE+-]+)", process.stdout).group(1))
        return {"rms": rms, "bmin": bmin}

    @staticmethod
    def auto_fov_shrink(context: Context, fits_path: str, rms: float, threshold_sigma: float=6.0, min_fov_pixels: int=256, min_area: int=6) -> Tuple[int, int]:
        """
        Analyzes whether the FOV can be iteratively halved using rectangular boxes.
        
        :param fits_path: Path to the monochromatic FITS file.
        :param rms: The known Root Mean Square noise of the image.
        :param threshold_sigma: SNR threshold to define a significant signal.
        :param min_fov_pixels: The minimum allowable width/height of the FOV.
        :param min_area: Minimum number of connected pixels to be considered a "signal".
        :return: The new (width, height) of the FOV.
        """
        with fits.open(fits_path) as hdul:
            data = hdul[0].data
            if data.ndim > 2:
                data = np.squeeze(data)
            ny, nx = data.shape
            current_ny, current_nx = ny, nx

            # Iteratively check if we can halve the FOV
            while True:
                next_ny, next_nx = current_ny // 2, current_nx // 2
                
                if next_nx < min_fov_pixels or next_ny < min_fov_pixels:
                    context.logger.debug(f"Reached minimum FOV limit ({min_fov_pixels} px). Stopping.")
                    return current_nx, current_ny  # although actually Difmap always outputs maps with x=y
                
                y_start = (ny - next_ny) // 2
                y_end = y_start + next_ny
                x_start = (nx - next_nx) // 2
                x_end = x_start + next_nx
                
                # Create a mask for the outer region
                outer_mask = np.ones((ny, nx), dtype=bool)
                outer_mask[y_start:y_end, x_start:x_end] = False
                
                # Extract outer data and create a binary map of significant pixels
                # Absolute values are used to catch significant negative artifacts as well
                significant_mask = (np.abs(data) > (threshold_sigma * rms)) & outer_mask
                
                # Label connected components
                labeled_array, num_features = label(significant_mask)
                
                # Check if any identified component meets the area requirement
                signal_detected = False
                max_found_area = 0
                
                if num_features > 0:
                    # Count pixels in each labeled component
                    component_sizes = np.bincount(labeled_array.ravel())
                    # Index 0 is the background, so we look at 1 onwards
                    if len(component_sizes) > 1:
                        max_found_area = np.max(component_sizes[1:])
                        if max_found_area >= min_area:
                            signal_detected = True

                if signal_detected:
                    context.logger.debug(f"Cannot shrink to {next_nx}x{next_ny}: signal found in outer region.")
                    return current_nx, current_ny  # although actually Difmap always outputs maps with x=y
                else:
                    context.logger.debug(f"OK to shrink to {next_nx}x{next_ny}: no signal found in outer region.")
                    current_ny, current_nx = next_ny, next_nx
