"""
run AIPS task TECOR
@Author: Jingdong Zhang
@DATE  : 2024/7/1
"""
# import pdb
from AIPS import AIPS
from AIPSTask import AIPSTask


def tecor(inname, inclass, inseq, indisk, infile, nfiles, gainver, gainuse):
    tecor_task = AIPSTask("TECOR")
    tecor_task.inname = inname
    tecor_task.inclass = inclass
    tecor_task.inseq = inseq
    tecor_task.indisk = indisk
    tecor_task.infile = infile
    tecor_task.nfiles = nfiles
    tecor_task.gainver = gainver
    tecor_task.gainuse = gainuse
    tecor_task.aparm[1:] = [1, 0]
    # pdb.set_trace()
    tecor_task.go()


if __name__ == "__main__":
    AIPS.userno = 2001
    tecor("BZ087A1", "UVDATA", 1, 1, "/data/aips_data/ionex/jplg3240.21i", 2, 4, 5)
