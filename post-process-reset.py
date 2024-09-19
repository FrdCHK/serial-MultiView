"""
reset post-process procedure
@Author: Jingdong Zhang
@DATE  : 2024/9/18
"""
import yaml
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

    command = f"rm {user_exp_dir}/*.csv {user_exp_dir}/*.fits {user_exp_dir}/*.jmfit"
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"\033[32m.csv, .fits, .jmfit files deleted under {user_exp_dir}\033[0m")
    except subprocess.CalledProcessError as e:
        print(e)

    print(f"\033[32mFinished, Please run RESET.001 in AIPS manually!\033[0m")
