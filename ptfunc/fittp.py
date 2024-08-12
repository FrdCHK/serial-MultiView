"""
run AIPS task FITTP
@Author: Jingdong Zhang
@DATE  : 2024/8/12
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def fittp(inname, inclass, inseq, indisk, dataout):
    jmfit_task = AIPSTask('FITTP')
    jmfit_task.inname = inname
    jmfit_task.inclass = inclass
    jmfit_task.inseq = inseq
    jmfit_task.indisk = indisk
    jmfit_task.dataout = dataout
    jmfit_task.go()
