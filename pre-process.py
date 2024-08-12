"""
ParselTongue pre-processing and calibration pipeline
designed for MultiView (VLBA obs.)
@Author: Jingdong Zhang
@DATE  : 2024/6/28
"""
import os
import sys
import math
from datetime import datetime, timedelta
import pandas as pd
import yaml
from AIPS import AIPS
from AIPSData import AIPSUVData, AIPSImage
import AIPSTV

import ptfunc
import tool


if __name__ == "__main__":
    print("\033[36m--------------------------------------")
    print("| ParselTongue script for MultiView: |")
    print("|    VLBA pre-processing pipeline    |")
    print("--------------------------------------\033[0m")

    # general config file
    with open('config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)

    AIPS.userno = config['aips_userno']

    # config file for user-exp
    user_exp_dir = f"./exp/{config['exp_name']}-{config['aips_userno']}"
    if not os.path.exists(user_exp_dir):
        os.mkdir(user_exp_dir)
        user_exp_config = {"aips_userno": 2001, "exp_name": config['exp_name'], "work_disk": 1,
                           "fits_file": "/data/aips_data/BZ087A/BZ087A1/bz087a1.idifits", "ncount": 1, "step": 0}
        with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
                  'w') as user_exp_config_file:
            yaml.safe_dump(user_exp_config, user_exp_config_file)
        print(f"created directory {user_exp_dir} and config file {config['exp_name']}-{config['aips_userno']}.yaml")
    else:
        user_exp_config_file_path = os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml")
        if not os.path.isfile(user_exp_config_file_path):
            raise FileNotFoundError(f"{config['exp_name']}-{config['aips_userno']}.yaml not found! Please clear all related files, directories and AIPS catalogues!")
        with open(user_exp_config_file_path, 'r') as user_exp_config_file:
            user_exp_config = yaml.safe_load(user_exp_config_file)
        print(f"\033[32mdirectory {user_exp_dir} and config file {config['exp_name']}-{config['aips_userno']}.yaml already exists, continue!\033[0m")

    step_id = user_exp_config['step'] + 1  # start from which step
    step_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 99]
    steps = pd.DataFrame({"ID": step_list,
                          "STEP": ["FITLD", "ACCOR", "APCAL", "PANG", "EOPS", "TECOR", "FRING (fringe finder)",
                                   "calibrator selection", "SPLAT", "FRING (calibrators)",
                                   "position offset", "SN export", "quit"]})
    print("\033[34m"+steps.to_string(index=False)+"\033[0m")
    while True:
        if user_exp_config['step'] >= step_list[-2]:
            print("\033[33mYou have already finished all steps...\033[0m")
            print("\033[33mWarning: you can only directly redo position offset.\033[0m")
            print("\033[33mIf you want to redo previous steps, please delete corresponding catalogs and extension files in AIPS!\033[0m")
            user_input = input(f"Please input the ID of starting step (redo):")
        else:
            user_input = input(f"Please input the ID of starting step ({user_exp_config['step'] + 1}):")
        if user_input != '':
            if tool.is_integer(user_input):
                step_id = int(user_input)
            else:
                print("\033[31mInvalid input!\033[0m")
                continue
        if step_id in step_list:
            if step_id == int(steps.loc[steps["STEP"] == "quit", "ID"].values[0]):
                print("quit!")
                sys.exit(0)
            elif step_id > (user_exp_config['step'] + 1):
                print("\033[31mPlease finish previous steps first!\033[0m")
            elif (step_id < 8) and (user_exp_config['step'] > 7):
                print("\033[31mWarning: please make sure you have manually deleted SN/CL tables for steps to be redone!\033[0m")
                while True:
                    user_input = input(f"y to continue, n/q to quit:")
                    if (user_input == 'Y') or (user_input == 'y'):
                        break
                    elif (user_input == 'N') or (user_input == 'n') or (user_input == 'Q') or (user_input == 'q'):
                        print("quit!")
                        sys.exit(0)
                break
            else:
                break
        else:
            print("\033[31mInvalid input!\033[0m")

    if step_id < 2:
        ptfunc.fitld(config['fits_file'], config['exp_name'], config['ncount'], config['work_disk'])
        user_exp_config["step"] = 1

    # current SN and CL table version
    snv = 0
    clv = 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # obs information (antannas, sources, obs date and day num, ...)
    data = AIPSUVData(config['exp_name'], "UVDATA", int(config['work_disk']), 1)
    antennas = data.antennas
    antennas = pd.DataFrame({"ID": range(1, len(antennas) + 1), "NAME": antennas})  # antenna list
    user_exp_config["antennas"] = antennas.to_dict()
    # TODO: in case refant is not in the pre-defined list, provide a menu for selection
    refant = tool.refant_select(antennas)
    user_exp_config["refant"] = int(refant)
    su_table = data.table('AIPS SU', 0)
    sources = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])  # source list
    for su_item in su_table:
        sources.loc[sources.index.size] = [su_item["id__no"], su_item["source"].rstrip(),
                                           su_item["raepo"], su_item["decepo"]]
    user_exp_config["sources"] = sources.to_dict()
    obs_date = data.header.date_obs
    obs_date = datetime.strptime(obs_date, "%Y-%m-%d")
    user_exp_config["obs_date"] = obs_date
    obs_year = obs_date.year  # obs year
    obs_doy = obs_date.timetuple().tm_yday  # day of year (first day of obs)
    nx_table = data.table('AIPS NX', 0)
    obs_day_num = int(nx_table[len(nx_table) - 1]['time'] + 1)  # obs day number
    user_exp_config["obs_day_num"] = obs_day_num

    if step_id < 3:
        ptfunc.accor(config['exp_name'], "UVDATA", 1, int(config['work_disk']), snv+1, clv, clv+1)
        user_exp_config["step"] = 2
    snv += 1
    clv += 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    if step_id < 4:
        ptfunc.apcal(config['exp_name'], "UVDATA", 1, int(config['work_disk']), snv+1, clv, clv+1)
        user_exp_config["step"] = 3
    snv += 1
    clv += 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    if step_id < 5:
        ptfunc.pang(config['exp_name'], "UVDATA", 1, int(config['work_disk']), clv, clv+1)
        user_exp_config["step"] = 4
    clv += 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # check whether EOP file exists and can cover the time range of the obs, if not, download with curl
    if step_id < 6:
        eop_full_dir = os.path.join(config["eop_dir"], "usno_finals.erp")
        try:
            eop_try_open = open(eop_full_dir, "r")
        except IOError as e:
            print(e)
            print("EOP file needs to be downloaded...")
            tool.eop_download(eop_full_dir)
            print("\033[32mDone!\033[0m")
        else:
            eop_try_open.close()
            eop_last_date = datetime.strptime(tool.eop_last_date(eop_full_dir), "%Y.%m.%d")
            obs_last_date = obs_date + timedelta(days=(obs_day_num-1))
            if eop_last_date < obs_last_date:
                print("EOP file needs to be updated...")
                os.remove(eop_full_dir)
                tool.eop_download(eop_full_dir)
            else:
                print("\033[32mCurrent EOP file is OK, continue!\033[0m")
        ptfunc.eops(config['exp_name'], "UVDATA", 1, int(config['work_disk']), clv, clv+1, eop_full_dir)
        user_exp_config["step"] = 5
    clv += 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # check whether ionex files exist and can cover the time range of the obs, if not, download with curl
    if step_id < 7:
        tool.ionex_download(config["ionex_dir"], obs_date, obs_day_num)
        ptfunc.tecor(config['exp_name'], "UVDATA", 1, int(config['work_disk']),
                     os.path.join(config["ionex_dir"], f"jplg{obs_doy:03d}0.{obs_year % 2000:02d}i"), 2, clv, clv+1)
        user_exp_config["step"] = 6
    clv += 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # FRING with fringe finder (the first scan)
    if step_id < 8:
        fringe_finder_name = sources.loc[sources['ID'] == nx_table[0]['source_id'], 'NAME'].values[0].rstrip()
        # NOTE AIPS timerange: the data points (2 sec) in a scan are not integrated, so, cover the whole scan!
        first_scan_end_time = nx_table[0]['time']+nx_table[0]['time_interval']/2+1e-3  # add extra ~1 min (unit: d)
        days, hours, minutes, seconds = tool.float_to_time_components(first_scan_end_time)
        ptfunc.fring(config['exp_name'], "UVDATA", 1, int(config['work_disk']), [fringe_finder_name],
                     [0, 0, 0, 0, days, hours, minutes, seconds], refant, [2, 0, 0, 0, 0, 0, 4],
                     [0, 0, 0, 0, 0, 0, 0, 0, -1], snv+1, clv, clv+1)
        user_exp_config["step"] = 7
    snv += 1
    clv += 1

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # select targets, calibrators, and primary calibrators (optional: POSSM)
    # pre-defined source list load/save
    if step_id < 9:
        predef_flag = True
        while True:
            user_input = input("Do you wish to load pre-defined source list? (y/n/q, defaults to n, q to quit):")
            if (user_input == 'Y') or (user_input == 'y'):
                break
            elif (user_input == 'N') or (user_input == 'n') or (user_input == ''):
                predef_flag = False
                break
            elif (user_input == 'Q') or (user_input == 'q'):
                with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
                          'w') as user_exp_config_file:
                    yaml.safe_dump(user_exp_config, user_exp_config_file)
                print("quit!")
                sys.exit(0)
            else:
                print("\033[31mInvalid input!\033[0m")

        if predef_flag:
            # load pre-defined source list
            with open(os.path.join("./predef", config["pre_def_file"]), 'r') as predef_file:
                predef = yaml.safe_load(predef_file)

            targets = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
            for key, value in predef.items():
                targets.loc[key] = sources.loc[sources["NAME"] == value["TARGET"]].iloc[0]
                # config files for each target
                target_config = {"ID": int(targets.loc[key, "ID"]), "NAME": str(targets.loc[key, "NAME"]),
                                 "RA": float(targets.loc[key, "RA"]), "DEC": float(targets.loc[key, "DEC"])}
                calibrators = sources.loc[sources["NAME"].isin(list(value["CALIBRATORS"].values()))]
                calibrators.reset_index(drop=True, inplace=True)
                target_config["CALIBRATORS"] = calibrators.to_dict()
                primary_calibrator = sources.loc[sources["NAME"] == value["PRIMARY_CALIBRATOR"]]
                primary_calibrator.reset_index(drop=True, inplace=True)
                # pdb.set_trace()
                target_config["PRIMARY_CALIBRATOR"] = primary_calibrator.to_dict()

                print(f"\033[32mPre-defined source list {os.path.join('./predef', config['pre_def_file'])} loaded!\033[0m")

                with open(os.path.join(user_exp_dir, f"{target_config['ID']}-{target_config['NAME']}.yaml"),
                          'w') as target_config_file:
                    yaml.safe_dump(target_config, target_config_file)
        else:
            # manual selection
            possm_flag = True
            while True:
                user_input = input("Do you wish to run POSSM when choosing primary calibrators? (y/n/q, defaults to y, q to quit):")
                if (user_input == 'Y') or (user_input == 'y') or (user_input == ''):
                    break
                elif (user_input == 'N') or (user_input == 'n'):
                    possm_flag = False
                    break
                elif (user_input == 'Q') or (user_input == 'q'):
                    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
                              'w') as user_exp_config_file:
                        yaml.safe_dump(user_exp_config, user_exp_config_file)
                    print("quit!")
                    sys.exit(0)
                else:
                    print("\033[31mInvalid input!\033[0m")

            target_num = tool.integer_input("Please input the number of targets")
            selected_sources = []  # to avoid repeated selection
            targets = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
            predef = {}
            for i in range(target_num):
                print("\033[34mSource list:")
                print(sources[["ID", "NAME"]].to_string(index=False)+"\033[0m")
                while True:
                    while True:
                        target_id = tool.integer_input(f"Target {i+1} ID")
                        if target_id in range(1, sources.index.size+1):
                            break
                        else:
                            print("\033[31mInvalid input!\033[0m")
                    if target_id in selected_sources:
                        print("\033[31mSource already selected!\033[0m")
                    else:
                        selected_sources.append(target_id)
                        targets.loc[targets.index.size] = (sources.loc[sources["ID"] == target_id]).iloc[0]
                        break
                # config files for each target
                target_config = {"ID": int(targets.loc[i, "ID"]), "NAME": str(targets.loc[i, "NAME"]),
                                 "RA": float(targets.loc[i, "RA"]), "DEC": float(targets.loc[i, "DEC"])}
                # select calibrators for each target
                calibrators = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
                while True:
                    redo_flag = False
                    user_input = input(f"Target {i+1} calibrator IDs (space separated):")
                    parts = user_input.split()
                    for part in parts:
                        if tool.is_integer(part):
                            int_part = int(part)
                            if int_part in selected_sources:
                                print(f"\033[31mSource {int_part} already selected!\033[0m")
                                redo_flag = True
                                break
                            elif not (int_part in range(1, sources.index.size+1)):
                                print("\033[31mInvalid input!\033[0m")
                                redo_flag = True
                                break
                        else:
                            print("\033[31mInvalid input!\033[0m")
                            redo_flag = True
                            break
                    if redo_flag:
                        continue
                    selected_sources += parts
                    for part in parts:
                        int_part = int(part)
                        calibrators.loc[calibrators.index.size] = (sources.loc[sources["ID"] == int_part]).iloc[0]
                    break
                target_config["CALIBRATORS"] = calibrators.to_dict()

                if possm_flag:
                    tv = AIPSTV.AIPSTV()
                    if not tv.exists():
                        tv.start()
                    ptfunc.possm(config['exp_name'], "UVDATA", 1, int(config['work_disk']), calibrators["NAME"].to_list(),
                                 [0, 1, 0, 0, -180, 180, 0, 0, 1], 1, tv, 4, 1, -1, clv)
                    if tv.exists():
                        tv.kill()
                # TODO: show distances to the target
                # TODO: POSSM显示的相位-频率图的离散度，有无可能定量描述并显示在这里？
                print("\033[34mCalibrator list:")
                print(calibrators[["ID", "NAME"]].to_string(index=False)+"\033[0m")

                # select primary calibrator for each target
                primary_calibrator = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
                while True:
                    primary_calibrator_id = tool.integer_input(f"Target {i+1} primary calibrator ID")
                    if primary_calibrator_id in calibrators["ID"].to_list():
                        primary_calibrator.loc[primary_calibrator.index.size] = (sources.loc[sources["ID"] == primary_calibrator_id]).iloc[0]
                        break
                    else:
                        print("\033[31mInvalid input!\033[0m")
                target_config["PRIMARY_CALIBRATOR"] = primary_calibrator.to_dict()

                with open(os.path.join(user_exp_dir, f"{target_config['ID']}-{target_config['NAME']}.yaml"),
                          'w') as target_config_file:
                    yaml.safe_dump(target_config, target_config_file)

                predef[i] = {"TARGET": str(targets.loc[i, "NAME"]),
                             "CALIBRATORS": calibrators["NAME"].to_dict(),
                             "PRIMARY_CALIBRATOR": primary_calibrator.loc[0, "NAME"]}

            # save pre-defined source list
            while True:
                user_input = input("Do you wish to save pre-defined source list? (y/n, defaults to n, q to quit):")
                if (user_input == 'Y') or (user_input == 'y'):
                    with open(os.path.join("./predef", config["pre_def_file"]), 'w') as predef_file:
                        yaml.safe_dump(predef, predef_file)
                    print(f"\033[32mPre-defined source list {predef_file} saved!\033[0m")
                    break
                elif (user_input == 'N') or (user_input == 'n') or (user_input == ''):
                    break
                else:
                    print("\033[31mInvalid input!\033[0m")

        user_exp_config["targets"] = targets.to_dict()
        user_exp_config["step"] = 8

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # SPLAT each target with its calibrators
    if step_id < 10:
        targets = pd.DataFrame.from_dict(user_exp_config["targets"])
        for i, row_i in targets.iterrows():
            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'r') as target_config_file:
                target_config = yaml.safe_load(target_config_file)

            sources_tar_cal = [target_config["NAME"]]
            cal = pd.DataFrame.from_dict(target_config["CALIBRATORS"])["NAME"].to_list()
            sources_tar_cal += cal
            ptfunc.splat(config['exp_name'], "UVDATA", 1, int(config['work_disk']),
                         sources_tar_cal, clv, target_config["NAME"], 1)

            user_exp_config["step"] = 9

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # FRING for each target: primary and secondary calibrators
    if step_id < 11:
        targets = pd.DataFrame.from_dict(user_exp_config["targets"])
        for i, row_i in targets.iterrows():
            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'r') as target_config_file:
                target_config = yaml.safe_load(target_config_file)

            # primary calibrator
            sn_splat = 0
            cl_splat = 1
            cal = pd.DataFrame.from_dict(target_config["CALIBRATORS"])
            ptfunc.fring(row_i['NAME'], "SPLAT", 1, int(config['work_disk']),
                         [target_config["PRIMARY_CALIBRATOR"]["NAME"][0]], [0], refant,
                         [2, 0, 1, 0, 0, 0, 4], [0], sn_splat+1, cl_splat, cl_splat+1)
            sn_splat += 1
            cl_splat += 1
            cal.loc[cal["NAME"] == target_config["PRIMARY_CALIBRATOR"]["NAME"][0], "SN"] = sn_splat

            # secondary calibrators
            for j, row_j in cal.iterrows():
                if row_j['NAME'] == target_config["PRIMARY_CALIBRATOR"]["NAME"][0]:
                    continue
                ptfunc.fring_only(row_i['NAME'], "SPLAT", 1, int(config['work_disk']),
                                  [row_j['NAME']], [0], refant,
                                  [2, 0, 1, 0, 1, 0, 4], [0, -1, -1], sn_splat+1, cl_splat)
                sn_splat += 1
                cal.loc[cal["NAME"] == row_j['NAME'], "SN"] = sn_splat

            # write SN version of each FRING result to target config files
            cal["SN"] = cal["SN"].astype(int)
            target_config["CALIBRATORS"] = cal.to_dict()
            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'w') as target_config_file:
                yaml.safe_dump(target_config, target_config_file)
            user_exp_config["step"] = 10

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    # determine ra and dec offset through IMAGR
    if step_id < 12:
        imagr_flag = True
        while True:
            user_input = input("Do you wish to run IMAGR with AIPSTV to determine RA and DEC offsets? (y/n/q, defaults to y, q to quit):")
            if (user_input == 'Y') or (user_input == 'y') or (user_input == ''):
                break
            elif (user_input == 'N') or (user_input == 'n'):
                imagr_flag = False
                break
            elif (user_input == 'Q') or (user_input == 'q'):
                with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
                          'w') as user_exp_config_file:
                    yaml.safe_dump(user_exp_config, user_exp_config_file)
                print("quit!")
                sys.exit(0)
            else:
                print("\033[31mInvalid input!\033[0m")

        targets = pd.DataFrame.from_dict(user_exp_config["targets"])
        for i, row_i in targets.iterrows():
            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'r') as target_config_file:
                target_config = yaml.safe_load(target_config_file)

            # check whether SPLIT, IBM001, and ICL001 exist, if so, delete first
            split_uv = AIPSUVData(row_i['NAME'], "SPLIT", int(config['work_disk']), 1)
            if split_uv.exists():
                split_uv.zap()
            ibm = AIPSImage(row_i['NAME'], "IBM001", int(config['work_disk']), 1)
            if ibm.exists():
                ibm.zap()
            icl = AIPSImage(row_i['NAME'], "ICL001", int(config['work_disk']), 1)
            if icl.exists():
                icl.zap()

            # split target
            ptfunc.split(row_i['NAME'], "SPLAT", 1, int(config['work_disk']), [row_i['NAME']], 2, [2, 0], 1)

            cellsize = 5e-4
            imsize = 512
            rashift = 0
            decshift = 0

            # IMAGR loop until user is satisfied with the parameters
            while True:
                if imagr_flag:
                    print(f"\033[34mRunning IMAGR with cellsize={cellsize:<8f}, imsize={imsize:<4d}, rashift={rashift:<8f}, and decshift={decshift:<8f}\033[0m")
                    tv = AIPSTV.AIPSTV()
                    if not tv.exists():
                        tv.start()
                    ptfunc.imagr(row_i['NAME'], "SPLIT", 1, int(config['work_disk']),
                                 row_i['NAME'], cellsize, imsize, 500, -4, rashift, decshift, tv=tv)
                    if tv.exists():
                        tv.kill()
                else:
                    rashift = tool.float_input(f"{row_i['NAME']} rashift (arcsec)", rashift)
                    decshift = tool.float_input(f"{row_i['NAME']} decshift (arcsec)", decshift)
                    target_config["RASHIFT"] = rashift
                    target_config["DECSHIFT"] = decshift
                    split_uv = AIPSUVData(row_i['NAME'], "SPLIT", int(config['work_disk']), 1)
                    if split_uv.exists():
                        split_uv.zap()
                    break

                imagr_adjust_flag = 1  # 0=N, 1=Y
                while True:
                    user_input = input(
                        "Do you wish to adjust IMAGR parameters? (y/n, defaults to y):")
                    if (user_input == 'Y') or (user_input == 'y') or (user_input == ''):
                        imagr_adjust_flag = 1
                        break
                    elif (user_input == 'N') or (user_input == 'n'):
                        imagr_adjust_flag = 0
                        break
                    else:
                        print("\033[31mInvalid input!\033[0m")

                if imagr_adjust_flag:
                    cellsize = tool.float_input("cellsize", cellsize)
                    imsize = tool.integer_input("imsize", imsize)
                    rashift = tool.float_input("rashift (arcsec)", rashift)
                    decshift = tool.float_input("decshift (arcsec)", decshift)

                    ibm = AIPSImage(row_i['NAME'], "IBM001", int(config['work_disk']), 1)
                    if ibm.exists():
                        ibm.zap()
                    icl = AIPSImage(row_i['NAME'], "ICL001", int(config['work_disk']), 1)
                    if icl.exists():
                        icl.zap()
                    continue
                else:
                    # after parameter adjustment is finished
                    cc_flag = 1  # 0=N, 1=Y
                    while True:
                        user_input = input(
                            "Do you wish to determine offsets automatically from clean component? (y/n, defaults to y):")
                        if (user_input == 'Y') or (user_input == 'y') or (user_input == ''):
                            cc_flag = 1
                            break
                        elif (user_input == 'N') or (user_input == 'n'):
                            cc_flag = 0
                            break
                        else:
                            print("\033[31mInvalid input!\033[0m")

                    if cc_flag:
                        icl = AIPSImage(row_i['NAME'], "ICL001", int(config['work_disk']), 1)
                        cc_table = icl.table("AIPS CC", 0)
                        rashift = cc_table[0]["deltax"] * 3.6e6  # original unit: degree, convert to mas
                        decshift = cc_table[0]["deltay"] * 3.6e6
                        target_config["RASHIFT"] = rashift
                        target_config["DECSHIFT"] = decshift

                        split_uv = AIPSUVData(row_i['NAME'], "SPLIT", int(config['work_disk']), 1)
                        if split_uv.exists():
                            split_uv.zap()
                        ibm = AIPSImage(row_i['NAME'], "IBM001", int(config['work_disk']), 1)
                        if ibm.exists():
                            ibm.zap()
                        icl = AIPSImage(row_i['NAME'], "ICL001", int(config['work_disk']), 1)
                        if icl.exists():
                            icl.zap()
                        break
                    else:
                        rashift = tool.float_input("rashift (arcsec)", rashift)
                        decshift = tool.float_input("decshift (arcsec)", decshift)
                        target_config["RASHIFT"] = rashift
                        target_config["DECSHIFT"] = decshift

                        split_uv = AIPSUVData(row_i['NAME'], "SPLIT", int(config['work_disk']), 1)
                        if split_uv.exists():
                            split_uv.zap()
                        ibm = AIPSImage(row_i['NAME'], "IBM001", int(config['work_disk']), 1)
                        if ibm.exists():
                            ibm.zap()
                        icl = AIPSImage(row_i['NAME'], "ICL001", int(config['work_disk']), 1)
                        if icl.exists():
                            icl.zap()
                        break

            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'w') as target_config_file:
                yaml.safe_dump(target_config, target_config_file)
            user_exp_config["step"] = 11

    # export SN
    if step_id < 13:
        targets = pd.DataFrame.from_dict(user_exp_config["targets"])
        for i, row_i in targets.iterrows():
            sn_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-SN")
            if not os.path.exists(sn_dir):
                os.mkdir(sn_dir)

            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'r') as target_config_file:
                target_config = yaml.safe_load(target_config_file)

            splat_uv = AIPSUVData(row_i['NAME'], "SPLAT", int(config['work_disk']), 1)
            primary_calibrator_id = int(target_config["PRIMARY_CALIBRATOR"]["ID"][0])
            calibrators = pd.DataFrame.from_dict(target_config["CALIBRATORS"])
            for j, row_j in calibrators.iterrows():
                if row_j["ID"] == primary_calibrator_id:  # do not export primary calibrator SN
                    continue
                sn_table = splat_uv.table('SN', int(row_j["SN"]))
                # get if number from FQ table header
                if_num = int(data.table("FQ", 1).keywords['NO_IF'])
                user_exp_config["if_number"] = if_num
                if_column = [f"p{if_id}" for if_id in range(if_num)]
                sn_df = pd.DataFrame(columns=['t', 'antenna', 'calsour']+if_column)
                for row_sn in sn_table:
                    if_value = [math.atan2(row_sn.imag1[if_id], row_sn.real1[if_id]) for if_id in range(if_num)]
                    sn_df.loc[sn_df.index.size] = [row_sn.time, row_sn.antenna_no, row_sn.source_id] + if_value
                sn_path = os.path.join(sn_dir, f"{target_config['ID']}-{target_config['NAME']}-SN{row_j['SN']}.csv")
                sn_df.to_csv(sn_path, index=False)
                print(f"\033[32mSN{row_j['SN']}({row_j['NAME']}) for target {target_config['NAME']} exported!\033[0m")

            target_config['MV_FLAG'] = False
            with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'w') as target_config_file:
                yaml.safe_dump(target_config, target_config_file)
            user_exp_config["step"] = 12

    # save exp config
    with open(os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml"),
              'w') as user_exp_config_file:
        yaml.safe_dump(user_exp_config, user_exp_config_file)

    print("\033[32mFinished!\033[0m")
