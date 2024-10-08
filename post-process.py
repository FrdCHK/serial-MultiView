"""
ParselTongue post-processing pipeline after MultiView (VLBA obs.)
@Author: Jingdong Zhang
@DATE  : 2024/8/9
"""
import os
import sys
import numpy as np
import scipy.interpolate as interp
import pandas as pd
import math
import yaml
from AIPS import AIPS
from Wizardry.AIPSData import AIPSUVData as WizAIPSData
import AIPSTV

import ptfunc
import tool


if __name__ == "__main__":
    print("\033[36m--------------------------------------")
    print("| ParselTongue script for MultiView: |")
    print("|      post-processing pipeline      |")
    print("--------------------------------------\033[0m")

    # general config file
    with open('config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)

    AIPS.userno = config['aips_userno']
    cellsize = float(config['cellsize'])
    imsize = int(config['imsize'])

    # config file for user-exp
    user_exp_dir = f"./exp/{config['exp_name']}-{config['aips_userno']}"
    user_exp_config_file_path = os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml")
    with open(user_exp_config_file_path, 'r') as user_exp_config_file:
        user_exp_config = yaml.safe_load(user_exp_config_file)
    antennas = pd.DataFrame.from_dict(user_exp_config['antennas'])

    targets = pd.DataFrame.from_dict(user_exp_config["targets"])
    for i, row_i in targets.iterrows():
        with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'r') as target_config_file:
            target_config = yaml.safe_load(target_config_file)
        if ('MV_FLAG' in target_config.keys()) and target_config['MV_FLAG']:
            # remove the antennas with no data for this target
            if 'ANTENNAS_EXCLUDE' in target_config.keys():
                antennas_exclude = pd.DataFrame.from_dict(target_config['ANTENNAS_EXCLUDE'])
                antennas_target = antennas[~antennas.isin(antennas_exclude.to_dict(orient='list')).all(axis=1)]
                antennas_target.reset_index(drop=True, inplace=True)
            else:
                antennas_target = antennas
            calibrators = pd.DataFrame.from_dict(target_config["CALIBRATORS"])

            # import MultiView SN table to AIPS
            mv_sn = calibrators.index.size + 1
            splat_data = WizAIPSData(target_config["NAME"], "SPLAT", int(config['work_disk']), 1)
            sn0 = splat_data.table('SN', 1)  # SN of primary calibrator's FRING
            sn_mv = splat_data.attach_table('SN', mv_sn)
            mv_dir = os.path.join(user_exp_dir, f"{target_config['ID']}-{target_config['NAME']}-MV")
            for row in sn0:
                an_id = row.antenna_no
                antenna_search = antennas_target.loc[antennas_target['ID'] == an_id]
                # pdb.set_trace()
                if antenna_search.empty or an_id == user_exp_config['refant']:
                    sn_mv.append(row)
                    continue
                an_name = antenna_search.loc[antennas_target['ID'] == an_id]['NAME'].item()
                tt = row.time
                sn_dir = os.path.join(mv_dir, f"{target_config['ID']}-{target_config['NAME']}-{an_id}-{an_name}.csv")
                sn_f = pd.read_csv(sn_dir)
                for j in range(int(user_exp_config["if_number"])):
                    phase0 = math.atan2(row.imag1[j], row.real1[j])
                    f = interp.interp1d(sn_f['t'], sn_f['phase'], bounds_error=False, fill_value="extrapolate")
                    phase = f(tt) + phase0
                    phase = (phase + np.pi) % (2 * np.pi) - np.pi
                    row.real1[j] = math.cos(phase)
                    row.imag1[j] = math.sin(phase)
                    row.real2[j] = math.cos(phase)
                    row.imag2[j] = math.sin(phase)
                sn_mv.append(row)
            sn0.close()
            sn_mv.close()
            print(f"\033[32mMultiView SN {mv_sn} for {target_config['NAME']} imported to AIPS!\033[0m")

            # CLCAL
            # CL2: primary calibrator FRING
            # CL3: MV FRING
            ptfunc.clcal_for_fring(row_i['NAME'], "SPLAT", 1, int(config['work_disk']),
                                   [target_config["PRIMARY_CALIBRATOR"]["NAME"][0]], [row_i['NAME']], mv_sn, 1, 3)

            # SPLIT (PR)
            ptfunc.split(row_i['NAME'], "SPLAT", 1, int(config['work_disk']), [row_i['NAME']], 2, [2, 0], 1)
            # UVFLG
            save_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-SAVE")
            conf_files = tool.find_matching_files(save_dir, f"{row_i['ID']}-{row_i['NAME']}")
            for item in conf_files:
                conf_dir = os.path.join(save_dir, item[0])
                with open(conf_dir, 'r') as an_conf_file:
                    an_conf = yaml.safe_load(an_conf_file)
                if 't_flag' not in an_conf.keys():
                    continue
                for timerange in an_conf['t_flag']:
                    timerang = [0 for _ in range(8)]
                    timerang[:4] = tool.float_to_time_components(timerange[0])
                    timerang[4:] = tool.float_to_time_components(timerange[1])
                    ptfunc.uvflg(row_i['NAME'], "SPLIT", 1, int(config['work_disk']), [item[1]], timerang)

            # IMAGR (PR)
            rashift = target_config["RASHIFT"]
            decshift = target_config["DECSHIFT"]

            tv = AIPSTV.AIPSTV()
            if not tv.exists():
                tv.start()
            ptfunc.imagr(row_i['NAME'], "SPLIT", 1, int(config['work_disk']),
                         row_i['NAME'], cellsize, imsize, 500, -4, rashift, decshift, tv=tv)
            if tv.exists():
                tv.kill()

            # whether run JMFIT
            # TODO: test whether this module works
            jmfit_flag = True
            while True:
                user_input = input(f"Do you want to run JMFIT for {row_i['NAME']}? (y/n, defaults to y):")
                if (user_input == 'Y') or (user_input == 'y') or (user_input == ''):
                    break
                elif (user_input == 'N') or (user_input == 'n'):
                    jmfit_flag = False
                    break
                else:
                    print("\033[31mInvalid input!\033[0m")

            # JMFIT (PR)
            if jmfit_flag:
                jm_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-PR.jmfit")
                ptfunc.jmfit(row_i['NAME'], "ICL001", 1, int(config['work_disk']), -3, 2, jm_dir)

            # FITTP (PR)
            img_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-PR.fits")
            ptfunc.fittp(row_i['NAME'], "ICL001", 1, int(config['work_disk']), img_dir)

            # SPLIT (MV)
            ptfunc.split(row_i['NAME'], "SPLAT", 1, int(config['work_disk']), [row_i['NAME']], 3, [2, 0], 2)
            # UVFLG
            for item in conf_files:
                conf_dir = os.path.join(save_dir, item[0])
                with open(conf_dir, 'r') as an_conf_file:
                    an_conf = yaml.safe_load(an_conf_file)
                if 't_flag' not in an_conf.keys():
                    continue
                for timerange in an_conf['t_flag']:
                    timerang = [0 for _ in range(8)]
                    timerang[:4] = tool.float_to_time_components(timerange[0])
                    timerang[4:] = tool.float_to_time_components(timerange[1])
                    ptfunc.uvflg(row_i['NAME'], "SPLIT", 2, int(config['work_disk']), [item[1]], timerang)

            # IMAGR (MV)
            rashift = target_config["RASHIFT"]
            decshift = target_config["DECSHIFT"]

            tv = AIPSTV.AIPSTV()
            if not tv.exists():
                tv.start()
            ptfunc.imagr(row_i['NAME'], "SPLIT", 2, int(config['work_disk']),
                         row_i['NAME'], cellsize, imsize, 500, -4, rashift, decshift, tv=tv)
            if tv.exists():
                tv.kill()

            # JMFIT (MV)
            if jmfit_flag:
                jm_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-MV.jmfit")
                ptfunc.jmfit(row_i['NAME'], "ICL001", 2, int(config['work_disk']), -3, 2, jm_dir)

                tool.summary(user_exp_dir, row_i)

            # FITTP (MV)
            img_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-MV.fits")
            ptfunc.fittp(row_i['NAME'], "ICL001", 2, int(config['work_disk']), img_dir)

        else:
            print(f"\033[33mYou have not run MultiView for target {row_i['NAME']}...\033[0m")
            sys.exit(0)

    # TODO: generate RESET file
    with open("./run/RESET.001", "w") as file:
        file.write('$ please set $RUNFIL="dir to this file" first, and type version="RUNFIL" in AIPS before run RESET\n')
        file.write(f"recat\nfor i=4 to 15;getn i;zap;end\ndefault extd;\ninclass 'SPLAT';\ninseq 1;\nindisk {int(config['work_disk'])};\n")
        for i, row_i in targets.iterrows():
            file.write(f"inname '{row_i['NAME']}';\ninext 'sn';\nextd\ninext 'cl';\nextd\n")
    print(f"\033[32mRESET.001 generated!\033[0m")

    print(f"\033[32mFinished!\033[0m")
