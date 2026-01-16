import pandas as pd
from multiprocessing import Process
from typing import List, Dict, Any
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import rc
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np
import copy
import AIPSTV

from core.Context import Context
from .SourceSelect import SourceSelect
from util.integer_input import integer_input


class MVPrimaryCalibratorSelect(SourceSelect):
    @classmethod
    def get_description(cls) -> str:
        return "Select MultiView primary calibrator."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start selecting MultiView primary calibrator")

        for target in context.get_context().get("targets"):
            calibrators = pd.DataFrame(target["CALIBRATORS"])
            if self.params.get("possm", False):
                target_params = {"inname": target["NAME"],
                                 "inclass": "SPLAT",
                                 "indisk": self.params["indisk"],
                                 "in_cat_ident": f"{target['NAME']} WITH CALIBRATORS"}
                context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, target_params)
                if not self.possm(context, calibrators["NAME"].to_list(), target_params):
                    context.logger.error(f"Error in MVPrimaryCalibratorSelect")
                    return False

            p = Process(target=self.sky_distri_plot, args=(target, "Sky distribution"))
            p.start()

            print(f"\033[34mCalibrators of target {target['NAME']}:")
            print(calibrators[["ID", "NAME"]].to_string(index=False)+"\033[0m")
            while True:
                primary_calibrator_id = integer_input(f"Primary calibrator ID")
                if primary_calibrator_id in calibrators["ID"].tolist():
                    break
                else:
                    print("\033[31mInvalid input!\033[0m")

            if p.is_alive():
                p.terminate()
                p.join()

            for source in context.get_context()["sources"]:
                if source["ID"] == primary_calibrator_id:
                    target["primary_calibrator"] = copy.deepcopy(source)
                    break

        context.logger.info(f"MultiView primary calibrator selection finished")
        return True

    def possm(self, context: Context, calibrator_list: List, params: Dict[str, Any]) -> bool:
        try:
            tv = AIPSTV.AIPSTV()
            if not tv.exists():
                tv.start()
            highst_cl_ver = context.get_context()["loaded_plugins"]["AipsCatalog"].get_highest_ext_ver(context,
                                                                                                       params["inname"],
                                                                                                       params["inclass"],
                                                                                                       params["indisk"],
                                                                                                       params["inseq"],
                                                                                                       "CL")
            task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "POSSM",
                                                                           "inname": params["inname"],
                                                                           "inclass": params["inclass"],
                                                                           "indisk": params["indisk"],
                                                                           "inseq": params["inseq"],
                                                                           "sources": calibrator_list,
                                                                           "aparm": [0, 1, 0, 0, -180, 180, 0, 0, 1],
                                                                           "dotv": 1,
                                                                           "tv": tv,
                                                                           "nplots": 9,
                                                                           "docalib": 1,
                                                                           "gainuse": highst_cl_ver,
                                                                           "stokes": "I",
                                                                           "solint": -1})
            task.run(context)
        except Exception as e:
            context.logger.error(f"Error in AIPS task POSSM: {e}")
            return False
        else:
            input("Press enter to continue...")
            if tv.exists():
                tv.kill()
            return True

    @staticmethod
    def sky_distri_plot(target: Dict[str, Any], title: str="Matplotlib Plot"):
        """在 tkinter 窗口中显示 matplotlib 图像"""

        root = tk.Tk()
        root.attributes('-type', 'utility')
        root.title(title)

        rc('font', size=10)
        rc('xtick', direction='in')
        rc('ytick', direction='in')

        target_coord = SkyCoord(ra=target["RA"], dec=target["DEC"], unit=[u.hourangle, u.deg], frame='icrs')
        calibrators = pd.DataFrame(target["CALIBRATORS"])
        calibrator_coords = SkyCoord(ra=calibrators["RA"], dec=calibrators["DEC"], unit=[u.hourangle, u.deg], frame='icrs')

        w = WCS(naxis=2)
        w.wcs.crval = [target_coord.ra.value, target_coord.dec.value]
        w.wcs.crpix = [500, 500]
        w.wcs.cdelt = np.array([-0.002, 0.002])
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]

        fig = Figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection=w)
        ax.set_xlabel("RA")
        ax.set_ylabel("DEC")

        ax.coords.grid(True, color="gray", ls="--", alpha=0.5)
        ax.coords[0].set_format_unit(u.hourangle)
        ax.coords[1].set_format_unit(u.deg)

        xpix, ypix = w.world_to_pixel(target_coord)
        ax.plot(xpix, ypix, marker="^", markersize=8, color="#A52C2C")
        ax.text(xpix, ypix - 140, f"TARGET\n{target['NAME']}", ha="center", va="center")

        xpix, ypix = w.world_to_pixel(calibrator_coords)
        for i, (x, y) in enumerate(zip(xpix, ypix)):
            ax.plot(x, y, marker="o", markersize=8, color="#238823")
            ax.text(x, y - 80, f"{calibrators.at[i, 'ID']} {calibrators.at[i, 'NAME']}", ha="center", va="center")

        ax.tick_params(axis='x', pad=6)

        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        root.mainloop()
