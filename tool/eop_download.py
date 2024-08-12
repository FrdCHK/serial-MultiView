"""
download eop file with curl
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
import sys
import pycurl


def eop_download(save_path):
    with open(save_path, 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, "ftp://gdc.cddis.eosdis.nasa.gov/vlbi/gsfc/ancillary/solve_apriori/usno_finals.erp")
        c.setopt(c.USERPWD, "anonymous:daip@nrao.edu")
        c.setopt(c.FTP_SSL, pycurl.FTPSSL_ALL)
        c.setopt(c.WRITEDATA, f)
        c.perform()
        c.close()
    try:
        eop_try_open = open(save_path, "r")
    except IOError as e:
        print(e)
        print("\033[31mEOP file download fails!\033[0m")
        sys.exit(1)
    else:
        eop_try_open.close()


if __name__ == "__main__":
    pass
