"""
run AIPS task SPLAT
@Author: Jingdong Zhang
@DATE  : 2024/7/4
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def splat(inname, inclass, inseq, indisk, sources, gainuse, outname, outseq, outdisk=None, docalib=1):
    splat_task = AIPSTask("SPLAT")
    splat_task.inname = inname
    splat_task.inclass = inclass
    splat_task.inseq = inseq
    splat_task.indisk = indisk
    splat_task.sources[1:] = sources
    splat_task.gainuse = gainuse
    splat_task.outname = outname
    splat_task.outseq = outseq
    if outdisk is None:
        outdisk = indisk
    splat_task.outdisk = outdisk
    splat_task.docalib = docalib
    splat_task.go()


if __name__ == "__main__":
    pass
