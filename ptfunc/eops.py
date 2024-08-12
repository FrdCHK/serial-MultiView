"""
run AIPS task CLCOR (opcode: EOPS)
@Author: Jingdong Zhang
@DATE  : 2024/7/1
"""
# import pdb
from AIPS import AIPS
from AIPSTask import AIPSTask


def eops(inname, inclass, inseq, indisk, gainver, gainuse, infile):
    eops_task = AIPSTask("CLCOR")
    eops_task.inname = inname
    eops_task.inclass = inclass
    eops_task.inseq = inseq
    eops_task.indisk = indisk
    eops_task.gainver = gainver
    eops_task.gainuse = gainuse
    eops_task.opcode = "EOPS"
    # pdb.set_trace()
    eops_task.infile = infile
    eops_task.go()


if __name__ == "__main__":
    AIPS.userno = 2001
    eops("BZ087A1", "UVDATA", 1, 1, 3, 4, "/data/aips_data/files/usno_finals.erp")
