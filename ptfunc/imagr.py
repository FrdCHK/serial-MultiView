"""
run AIPS task IMAGR
@Author: Jingdong Zhang
@DATE  : 2024/7/10
"""
# import pdb
from AIPS import AIPS
from AIPSTask import AIPSTask


def imagr(inname, inclass, inseq, indisk, source, cellsize, imsize, niter, ltype, rashift, decshift, docalib=-1, gainuse=0, tv=None):
    imagr_task = AIPSTask('IMAGR')
    imagr_task.inname = inname
    imagr_task.inclass = inclass
    imagr_task.inseq = inseq
    imagr_task.indisk = indisk
    imagr_task.docalib = docalib
    imagr_task.gainuse = gainuse
    imagr_task.srcname = source
    imagr_task.cellsize[1:] = [cellsize, cellsize]
    imagr_task.imsize[1:] = [imsize, imsize]
    imagr_task.niter = niter
    imagr_task.nfield = 1
    imagr_task.ltype = ltype
    imagr_task.rashift[1] = rashift
    imagr_task.decshift[1] = decshift

    if tv is not None:
        imagr_task.dotv = 1
        imagr_task.tv = tv

    # pdb.set_trace()
    imagr_task.go()


if __name__ == "__main__":
    pass
