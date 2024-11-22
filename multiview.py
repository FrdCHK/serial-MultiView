"""
main pipeline for serial-MultiView
@Author: Jingdong Zhang
@DATE  : 2024/7/15
"""
# import pdb
import yaml
import sys
import os
import pandas as pd
from matplotlib import rc

import mv
import tool


if __name__ == "__main__":
    print("\033[36m--------------------")
    print("| serial-MultiView |")
    print("--------------------\033[0m")

    # matplotlib initialization
    # font_control = {'family': 'Times New Roman', 'size': 18}
    font_control = {'size': 12}
    rc('font', **font_control)
    # rc('mathtext', **{'fontset': 'dejavuserif'})
    rc('xtick', direction='in')
    rc('ytick', direction='in')

    # general config file
    with open('config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)

    # config file for user-exp
    user_exp_dir = f"./exp/{config['exp_name']}-{config['aips_userno']}"
    user_exp_config_dir = os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml")
    with open(user_exp_config_dir, 'r') as user_exp_config_file:
        user_exp_config = yaml.safe_load(user_exp_config_file)

    # loop targets
    targets = pd.DataFrame.from_dict(user_exp_config["targets"])
    for i, row_i in targets.iterrows():
        with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'r') as target_config_file:
            target_config = yaml.safe_load(target_config_file)

        # have already run mv?
        run_all_flag = True
        if ('MV_FLAG' in target_config.keys()) and target_config['MV_FLAG']:
            print(f"\033[33mYou have already run this script for target {row_i['NAME']}...\033[0m")
            while True:
                user_input = input(f"Do you want to rerun for all antennas? (y/n/q, defaults to n, q to quit):")
                if (user_input == 'Y') or (user_input == 'y'):
                    break
                elif (user_input == 'N') or (user_input == 'n') or (user_input == ''):
                    run_all_flag = False
                    break
                elif (user_input == 'Q') or (user_input == 'q'):
                    print("quit!")
                    sys.exit(0)
                else:
                    print("\033[31mInvalid input!\033[0m")

        # instantiate calibrator objects
        calibrator_table = pd.DataFrame.from_dict(target_config["CALIBRATORS"])
        secondary_calibrators = []
        if_column = [f"p{if_id}" for if_id in range(user_exp_config["if_number"])]
        sn_all = pd.DataFrame(columns=['t', 'antenna', 'calsour'] + if_column)
        sn_dir = os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}-SN")
        for j, row_j in calibrator_table.iterrows():
            if row_j['ID'] == target_config["PRIMARY_CALIBRATOR"]["ID"][0]:
                continue
            sn_path = os.path.join(sn_dir, f"{row_i['ID']}-{row_i['NAME']}-SN{row_j['SN']}.csv")
            sn_table = pd.read_csv(sn_path)
            sn_table = sn_table.loc[sn_table['p0'] != 0]
            calibrator = mv.Calibrator(row_j['ID'], row_j['NAME'], row_j['RA'], row_j['DEC'], row_j['SN'], sn_table)
            calibrator.calc_relative_position(target_config["PRIMARY_CALIBRATOR"]["RA"][0],
                                              target_config["PRIMARY_CALIBRATOR"]["DEC"][0])
            secondary_calibrators.append(calibrator)
            sn_all = pd.concat([sn_all, sn_table])

        sn_all['antenna'] = sn_all['antenna'].astype(int)
        sn_all['calsour'] = sn_all['calsour'].astype(int)

        # add relative position columns
        for j in range(len(secondary_calibrators)):
            sn_all.loc[sn_all['calsour'] == secondary_calibrators[j].id, ['x', 'y']] = [secondary_calibrators[j].dx,
                                                                                        secondary_calibrators[j].dy]

        # instantiate antenna objects
        antenna_table = pd.DataFrame.from_dict(user_exp_config["antennas"])
        antennas = []
        antennas_exclude = pd.DataFrame(columns=['ID', 'NAME'])  # mark the antennas with no data for this target
        for j, row_j in antenna_table.iterrows():
            if row_j['ID'] == user_exp_config["refant"]:
                continue
            sn_antenna = sn_all.loc[sn_all['antenna'] == row_j['ID']]
            if sn_antenna.shape[0] <= 10:  # to ensure enough data for extension
                antennas_exclude.loc[antennas_exclude.index.size] = [row_j['ID'], row_j['NAME']]
                continue
            sn_if0 = sn_antenna[['calsour', 'x', 'y', 't']].copy(deep=True)
            sn_if0['phase'] = sn_antenna['p0']  # use the first IF only
            sn_if0.sort_values(by='t', inplace=True, ascending=True)
            sn_if0.reset_index(drop=True, inplace=True)
            antenna = mv.Antenna(row_j['ID'], row_j['NAME'], sn_if0, secondary_calibrators)
            antennas.append(antenna)

        target_config['ANTENNAS_EXCLUDE'] = antennas_exclude.to_dict()

        target_relative_position = tool.relative_position([target_config["PRIMARY_CALIBRATOR"]["RA"][0],
                                                           target_config["PRIMARY_CALIBRATOR"]["DEC"][0]],
                                                          [target_config['RA'], target_config['DEC']])
        if run_all_flag:
            for j, item in enumerate(antennas):
                gui = mv.Gui({'ID': row_i['ID'], 'NAME': row_i['NAME']},
                             item, config, target_relative_position, secondary_calibrators, target_config['MV_FLAG'])
        else:
            antenna_ids = []
            while True:
                end_flag = False
                for item in antennas:
                    print(f"\033[34m{item.id:>2d} {item.name}\033[0m")
                    antenna_ids.append(item.id)
                print(f"\033[34m99 end\033[0m")
                while True:
                    user_input = tool.integer_input("Select an antenna (ID) to rerun")
                    if user_input in antenna_ids:
                        antenna_index = antenna_ids.index(user_input)
                        gui = mv.Gui({'ID': row_i['ID'], 'NAME': row_i['NAME']},
                                     antennas[antenna_index], config, target_relative_position, secondary_calibrators,
                                     target_config['MV_FLAG'])
                        break
                    elif user_input == 99:
                        end_flag = True
                        break
                    else:
                        print("\033[31mInvalid input!\033[0m")
                if end_flag:
                    break

        target_config['MV_FLAG'] = True
        with open(os.path.join(user_exp_dir, f"{row_i['ID']}-{row_i['NAME']}.yaml"), 'w') as target_config_file:
            yaml.safe_dump(target_config, target_config_file)

    print("\033[32mFinished!\033[0m")
