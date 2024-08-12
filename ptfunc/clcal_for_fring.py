"""
run AIPS task FRING
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def clcal_for_fring(inname, inclass, inseq, indisk, calsour, sources, snver, gainver, gainuse):
    clcal_task = AIPSTask('CLCAL')
    clcal_task.inname = inname
    clcal_task.inclass = inclass
    clcal_task.inseq = inseq
    clcal_task.indisk = indisk
    clcal_task.calsour[1:] = calsour
    clcal_task.sources[1:] = sources
    clcal_task.opcode = "CALP"
    clcal_task.interpol = "AMBG"
    clcal_task.smotyp = "VLBI"
    clcal_task.samptype = "BOX"
    clcal_task.bparm[1:] = [0, 0, 1, 0]
    clcal_task.snv = snver
    clcal_task.gainver = gainver
    clcal_task.gainuse = gainuse
    clcal_task.go()


if __name__ == "__main__":
    pass
