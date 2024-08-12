"""
run AIPS task FITLD
@Author: Jingdong Zhang
@DATE  : 2024/6/28
"""
import sys
from AIPS import AIPS
from AIPSTask import AIPSTask
# from AIPSData import AIPSUVData


def fitld(datain, outname, ncount=1, outdisk=1):
    # check whether the file exists
    try:
        datain_try_open = open(datain, "r")
    except IOError as e:
        print(e)
        sys.exit(1)
    else:
        datain_try_open.close()

    # run fitld
    fitld_task = AIPSTask('FITLD')
    fitld_task.datain = datain
    fitld_task.outname = outname
    fitld_task.outclass = "UVDATA"
    fitld_task.outdisk = int(outdisk)
    fitld_task.ncount = ncount
    if ncount > 1:
        fitld_task.doconcat = 1

    fitld_task.go()


if __name__ == "__main__":
    AIPS.userno = 2001

    # check whether data already exists in AIPS
    # data = AIPSUVData(config['exp_name'], "UVDATA", int(config['work_disk']), 1)
    # if data.exists():
    #     data.clrstat()
    #     data.zap()
    #     raise RuntimeError("Data already exists in AIPS!")

    # fitld("/data/aips_data/V636A/V636A.FITS.1", "V636A", ncount=2)
    fitld("/data/aips_data/BZ087A/BZ087A1/bz087a1.idifits", "BZ087A1")
