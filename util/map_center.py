from typing import Dict, Any
from AIPSData import AIPSImage

from core.Context import Context
from util.yes_no_input import yes_no_input
from util.integer_input import integer_input
from util.float_input import float_input


def map_center(context: Context, target: Dict[str, Any], split_cat_ident: str, indisk: int) -> bool:
    cellsize = 5e-4
    imsize = 512
    rashift = 0
    decshift = 0

    try:
        # IMAGR loop until user is satisfied with the parameters
        while True:
            if yes_no_input("Do you wish to run IMAGR with AIPSTV to determine RA and DEC offsets?", default=True):
                print(f"\033[34mRunning IMAGR with cellsize={cellsize:<8f}, imsize={imsize:<4d}, rashift={rashift:<8f}, and decshift={decshift:<8f}\033[0m")
                task_imagr = context.get_context()["loaded_plugins"]["Imagr"]({"inname": target["NAME"],
                                                                               "inclass": "SPLIT",
                                                                               "indisk": indisk,
                                                                               "in_cat_ident": split_cat_ident,
                                                                               "srcname": target["NAME"],
                                                                               "cellsize": [cellsize, cellsize],
                                                                               "imsize": [imsize, imsize],
                                                                               "nfield": 1,
                                                                               "niter": 500,
                                                                               "ltype": -4,
                                                                               "rashift": [rashift],
                                                                               "decshift": [decshift],
                                                                               "dotv": 1,
                                                                               "out_cat_ident": "TEMP"})
                task_imagr.run(context)
            else:
                rashift = float_input(f"{target['NAME']} rashift (arcsec)", rashift)
                decshift = float_input(f"{target['NAME']} decshift (arcsec)", decshift)
                target["rashift"] = rashift
                target["decshift"] = decshift
                break

            params_target = {"in_cat_ident": "TEMP"}
            context.get_context()["loaded_plugins"]["AipsCatalog"].ident2cat(context, params_target)
            ibm = AIPSImage(target['NAME'], "IBM001", indisk, params_target['inseq'])
            icl = AIPSImage(target['NAME'], "ICL001", indisk, params_target['inseq'])
            if yes_no_input("Do you wish to adjust IMAGR parameters?", default=True):
                cellsize = float_input("cellsize", cellsize)
                imsize = integer_input("imsize", imsize)
                rashift = float_input("rashift (arcsec)", rashift)
                decshift = float_input("decshift (arcsec)", decshift)
                if ibm.exists():
                    ibm.zap()
                    context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "IBM001", indisk, params_target['inseq'])
                if icl.exists():
                    icl.zap()
                    context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "ICL001", indisk, params_target['inseq'])
                continue
            else:
                if yes_no_input("Do you wish to determine offsets automatically from clean component? Make sure you have cleaned during IMAGR.", default=True):
                    if icl.exists():
                        cc_table = icl.table("AIPS CC", 0)
                        rashift = cc_table[0]["deltax"] * 3600
                        decshift = cc_table[0]["deltay"] * 3600
                        target["rashift"] = rashift
                        target["decshift"] = decshift
                else:
                    rashift = float_input(f"{target['NAME']} rashift (arcsec)", rashift)
                    decshift = float_input(f"{target['NAME']} decshift (arcsec)", decshift)
                    target["rashift"] = rashift
                    target["decshift"] = decshift
                if ibm.exists():
                    ibm.zap()
                    context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "IBM001", indisk, params_target['inseq'])
                if icl.exists():
                    icl.zap()
                    context.get_context()["loaded_plugins"]["AipsCatalog"].del_catalog(context, target['NAME'], "ICL001", indisk, params_target['inseq'])
                break
    except Exception as e:
        context.logger.error(f"Error in map center determination: {e}")
        return False
    else:
        context.logger.debug(f"Map center determined: {rashift:<8f}, {decshift:<8f}")
        return True
