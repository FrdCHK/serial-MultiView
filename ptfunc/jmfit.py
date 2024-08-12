"""
run AIPS task JMFIT
@Author: Jingdong Zhang
@DATE  : 2024/7/10
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def jmfit(inname, inclass, inseq, indisk, doprint, prtlev, fitout=None):
    jmfit_task = AIPSTask('JMFIT')
    jmfit_task.inname = inname
    jmfit_task.inclass = inclass
    jmfit_task.inseq = inseq
    jmfit_task.indisk = indisk
    jmfit_task.doprint = doprint
    jmfit_task.prtlev = prtlev
    if fitout is not None:
        jmfit_task.fitout = fitout
    jmfit_task.go()


if __name__ == "__main__":
    pass
