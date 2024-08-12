"""
run AIPS task POSSM
@Author: Jingdong Zhang
@DATE  : 2024/7/3
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def possm(inname, inclass, inseq, indisk, sources, aparm, dotv, tv, nplots, docalib, solint, gainuse):
    possm_task = AIPSTask('POSSM')
    possm_task.inname = inname
    possm_task.inclass = inclass
    possm_task.inseq = inseq
    possm_task.indisk = indisk
    possm_task.sources[1:] = sources
    possm_task.aparm[1:] = aparm
    possm_task.dotv = dotv
    possm_task.tv = tv
    possm_task.nplots = nplots
    possm_task.docalib = docalib
    possm_task.gainuse = gainuse
    possm_task.stokes = 'I'
    possm_task.solint = solint
    possm_task.go()
