"""
only FRING no CLCAL
@Author: Jingdong Zhang
@DATE  : 2024/7/9
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def fring_only(inname, inclass, inseq, indisk, calsour, timerang, refant, aparm, dparm, snver, gainuse):
    fring_task = AIPSTask('FRING')
    fring_task.inname = inname
    fring_task.inclass = inclass
    fring_task.inseq = inseq
    fring_task.indisk = indisk
    fring_task.calsour[1:] = calsour
    fring_task.timerang[1:] = timerang
    fring_task.refant = float(refant)
    fring_task.aparm[1:] = aparm
    fring_task.dparm[1:] = dparm
    fring_task.solint = -1
    fring_task.docalib = 1
    fring_task.snver = snver
    fring_task.gainuse = gainuse
    fring_task.go()


if __name__ == "__main__":
    pass
