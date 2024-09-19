"""
run AIPS task UVFLG
@Author: Jingdong Zhang
@DATE  : 2024/9/19
"""
from AIPS import AIPS
from AIPSTask import AIPSTask


def uvflg(inname, inclass, inseq, indisk, antennas, timerang):
    uvflg_task = AIPSTask('UVFLG')
    uvflg_task.inname = inname
    uvflg_task.inclass = inclass
    uvflg_task.inseq = inseq
    uvflg_task.indisk = indisk
    uvflg_task.outfgver = 1
    uvflg_task.opcode = 'flag'
    uvflg_task.antennas[1:] = antennas
    uvflg_task.timerang[1:] = timerang
    uvflg_task.go()
