"""
run AIPS task APCAL
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def apcal(inname, inclass, inseq, indisk, snver, gainver, gainuse, tyver=1, gcver=1):
    apcal_task = AIPSTask('APCAL')
    apcal_task.inname = inname
    apcal_task.inclass = inclass
    apcal_task.inseq = inseq
    apcal_task.indisk = indisk
    apcal_task.snv = snver
    apcal_task.tyver = tyver
    apcal_task.gcver = gcver
    apcal_task.go()

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
    pass
