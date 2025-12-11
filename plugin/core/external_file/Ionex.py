import pycurl
from pycurl import error as pycurl_error
from datetime import timedelta
import os

from core.Plugin import Plugin
from core.Context import Context
from util.unzip import unzip


class Ionex(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Check ionex file availability. Download ionex file if not available. A parameter ionex_dir is required."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start ionex file preparation")
        for i in range(context.get_context()["obs_time"]["day_num"]):
            d = context.get_context()["obs_time"]["date"] + timedelta(days=i)
            year = d.year
            doy = d.timetuple().tm_yday
            fname = f"jplg{doy:03d}0.{year % 2000:02d}i"
            ionex_full_path = os.path.join(self.params["ionex_dir"], fname)
            try:
                ionex_try_open = open(ionex_full_path, "r")
            except IOError:
                context.logger.info(f"Ionex file {fname} needs to be downloaded")
                url = f"ftp://gdc.cddis.eosdis.nasa.gov/gps/products/ionex/{year:4d}/{doy:03d}/"
                if year < 2023 or (year == 2023 and doy < 220):
                    download_name = f"jplg{doy:03d}0.{year % 2000:02d}i.Z"
                    download_full_dir = os.path.join(self.params["ionex_dir"], f"{fname}.Z")
                else:
                    download_name = f"JPL0OPSFIN_{year:4d}{doy:03d}0000_01D_02H_GIM.INX.gz"
                    download_full_dir = os.path.join(self.params["ionex_dir"], f"{fname}.gz")
                with open(download_full_dir, 'wb') as f:
                    try:
                        c = pycurl.Curl()
                        c.setopt(c.URL, url + download_name)
                        c.setopt(c.USERPWD, "anonymous:daip@nrao.edu")
                        c.setopt(c.FTP_SSL, pycurl.FTPSSL_ALL)
                        c.setopt(c.WRITEDATA, f)
                        c.setopt(c.TIMEOUT, 120)
                        c.setopt(c.CONNECTTIMEOUT, 30)
                        c.perform()
                    except pycurl_error as e:
                        context.logger.error(f"Ionex file {fname} download failed: {e}")
                        return False
                    else:
                        c.close()
                try:
                    downloaded_ionex_try_open = open(download_full_dir, "r")
                except IOError:
                    context.logger.error(f"Ionex file {fname} download failed")
                    return False
                else:
                    downloaded_ionex_try_open.close()
                    unzip(context, download_full_dir)
                    context.logger.info(f"Ionex file {fname} downloaded")
            else:
                ionex_try_open.close()
                context.logger.info(f"Ionex file {fname} already exists")

        context.logger.info(f"Ionex file preparation finished")
        return True
