"""
reset post-process procedure
@Author: Jingdong Zhang
@DATE  : 2024/9/18
"""
import os
import yaml
import pandas as pd
import subprocess


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

    # TODO: generate RESET file
    with open("./run/RESET.001", "w") as file:
        file.write("$ please set $RUNFIL='dir to this file' first, and type version='RUNFIL' in AIPS before run RESET\n")
        file.write(f"recat\nfor i=4 to 15;getn i;zap;end\ndefault extd;\ninclass 'SPLAT';\ninseq 1;\nindisk {int(config['work_disk'])};\n")
        for i, row_i in targets.iterrows():
            file.write(f"inname '{row_i['NAME']}';\ninext 'sn';\nextd\ninext 'cl';\nextd\n")
    print(f"\033[32mRESET.001 generated!\033[0m")

    print(f"\033[32mFinished, Please run RESET.001 in AIPS manually!\033[0m")
