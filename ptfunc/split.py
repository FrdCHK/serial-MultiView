"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/10
"""
# import pdb
from AIPS import AIPS
from AIPSTask import AIPSTask


def split(inname, inclass, inseq, indisk, sources, gainuse, aparm, outseq, outdisk=None, docalib=1):
    split_task = AIPSTask("SPLIT")
    split_task.inname = inname
    split_task.inclass = inclass
    split_task.inseq = inseq
    split_task.indisk = indisk
    split_task.sources[1:] = sources
    split_task.gainuse = gainuse
    # pdb.set_trace()
    split_task.aparm[1:] = aparm
    # pdb.set_trace()
    split_task.outseq = outseq
    if outdisk is None:
        outdisk = indisk
    split_task.outdisk = outdisk
    split_task.docalib = docalib
    split_task.go()


if __name__ == "__main__":
    pass
