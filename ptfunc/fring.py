"""
run AIPS task FRING
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def fring(inname, inclass, inseq, indisk, calsour, timerang, refant, aparm, dparm, snver, gainver, gainuse):
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
    fring_task.gainuse = gainver  # note: gainver of FRING = gainuse of CLCAL
    fring_task.go()

    clcal_task = AIPSTask('CLCAL')
    clcal_task.inname = inname
    clcal_task.inclass = inclass
    clcal_task.inseq = inseq
    clcal_task.indisk = indisk
    clcal_task.calsour[1:] = calsour
    clcal_task.opcode = "CALP"
    clcal_task.interpol = "AMBG"
    clcal_task.smotyp = "VLBI"
    clcal_task.bparm[1:] = [0, 0, 1, 0]
    # clcal_task.dobtween = 1
    clcal_task.snv = snver
    clcal_task.gainver = gainver
    clcal_task.gainuse = gainuse
    clcal_task.go()


if __name__ == "__main__":
    pass
