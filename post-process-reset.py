"""
reset post-process procedure
@Author: Jingdong Zhang
@DATE  : 2024/9/18
"""
import os
import yaml
import pandas as pd
import subprocess
from AIPS import AIPS
from AIPSData import AIPSUVData, AIPSImage


if __name__ == "__main__":
    print("\033[36m--------------------------------------")
    print("| ParselTongue script for MultiView: |")
    print("|        post-processing reset       |")
    print("--------------------------------------\033[0m")

    # general config file
    with open('config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)
    user_exp_dir = f"./exp/{config['exp_name']}-{config['aips_userno']}"
    user_exp_config_file_path = os.path.join(user_exp_dir, f"{config['exp_name']}-{config['aips_userno']}.yaml")
    with open(user_exp_config_file_path, 'r') as user_exp_config_file:
        user_exp_config = yaml.safe_load(user_exp_config_file)
    targets = pd.DataFrame.from_dict(user_exp_config["targets"])

    command = f"rm {user_exp_dir}/*.csv {user_exp_dir}/*.fits {user_exp_dir}/*.jmfit"
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"\033[32m.csv, .fits, .jmfit files deleted under {user_exp_dir}\033[0m")
    except subprocess.CalledProcessError as e:
        print(e)

    # remove tables and files in AIPS
    AIPS.userno = config['aips_userno']
    for i, row_i in targets.iterrows():
        # check whether SPLIT, IBM001, and ICL001 exist, if so, delete them
        for j in [1, 2]:  # PR and MV
            split_uv = AIPSUVData(row_i['NAME'], "SPLIT", int(config['work_disk']), j)
            if split_uv.exists():
                split_uv.zap()
            ibm = AIPSImage(row_i['NAME'], "IBM001", int(config['work_disk']), j)
            if ibm.exists():
                ibm.zap()
            icl = AIPSImage(row_i['NAME'], "ICL001", int(config['work_disk']), j)
            if icl.exists():
                icl.zap()
        # clear CL/SN in SPLAT
        splat_uv = AIPSUVData(row_i['NAME'], "SPLAT", int(config['work_disk']), 1)
        if splat_uv.exists():
            splat_uv.zap_table("SN", 0)
            splat_uv.zap_table("CL", 0)

    print(f"\033[32mFinished!\033[0m")
