"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
import os
import pycurl
from datetime import timedelta

from tool.unzip import unzip


def ionex_download(save_path, date, day_num):
    for i in range(day_num):
        d = date + timedelta(days=i)
        year = d.year
        doy = d.timetuple().tm_yday
        fname = f"jplg{doy:03d}0.{year % 2000:02d}i"
        ionex_full_dir = os.path.join(save_path, fname)

        try:
            ionex_try_open = open(ionex_full_dir, "r")
        except IOError as e:
            print(e)
            print("Ionex file needs to be downloaded...")
            url = f"ftp://gdc.cddis.eosdis.nasa.gov/gps/products/ionex/{year:4d}/{doy:03d}/"
            if year < 2023 or (year == 2023 and doy < 220):
                download_name = f"jplg{doy:03d}0.{year % 2000:02d}i.Z"
                download_full_dir = os.path.join(save_path, f"{fname}.Z")
            else:
                download_name = f"JPL0OPSFIN_{year:4d}{doy:03d}0000_01D_02H_GIM.INX.gz"
                download_full_dir = os.path.join(save_path, f"{fname}.gz")
            with open(download_full_dir, 'wb') as f:
                c = pycurl.Curl()
                c.setopt(c.URL, url + download_name)
                c.setopt(c.USERPWD, "anonymous:daip@nrao.edu")
                c.setopt(c.FTP_SSL, pycurl.FTPSSL_ALL)
                c.setopt(c.WRITEDATA, f)
                c.perform()
                c.close()
            unzip(download_full_dir)
            print("\033[32mDone!\033[0m")
        else:
            ionex_try_open.close()
            print(f"\033[32mIonex file {fname} already exists, continue!\033[0m")


if __name__ == "__main__":
    pass
