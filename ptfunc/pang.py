"""
run AIPS task CLCOR (opcode: PANG)
@Author: Jingdong Zhang
@DATE  : 2024/7/1
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def pang(inname, inclass, inseq, indisk, gainver, gainuse):
    pang_task = AIPSTask("CLCOR")
    pang_task.inname = inname
    pang_task.inclass = inclass
    pang_task.inseq = inseq
    pang_task.indisk = indisk
    pang_task.gainver = gainver
    pang_task.gainuse = gainuse
    pang_task.opcode = "PANG"
    pang_task.clcorprm[1:] = [1, 0]
    pang_task.go()


if __name__ == "__main__":
    AIPS.userno = 2001
    pang("BZ087A1", "UVDATA", 1, 1, 2, 3)
