"""
run AIPS task ACCOR
@Author: Jingdong Zhang
@DATE  : 2024/7/1
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def accor(inname, inclass, inseq, indisk, snver, gainver, gainuse):
    accor_task = AIPSTask('ACCOR')
    accor_task.inname = inname
    accor_task.inclass = inclass
    accor_task.inseq = inseq
    accor_task.indisk = indisk
    accor_task.go()

    clcal_task = AIPSTask('CLCAL')
    clcal_task.inname = inname
    clcal_task.inclass = inclass
    clcal_task.inseq = inseq
    clcal_task.indisk = indisk
    clcal_task.snv = snver
    clcal_task.gainver = gainver
    clcal_task.gainuse = gainuse
    clcal_task.go()


if __name__ == "__main__":
    AIPS.userno = 2001
    accor("BZ087A1", "UVDATA", 1, 1, 1, 1, 2)
