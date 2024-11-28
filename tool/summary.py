"""
read jmfit files and generate a summary csv file
@Author: Jingdong Zhang
@DATE  : 2024/8/12
"""
import os
import pandas as pd
import re


def summary(exp_dir, target_row, pr_flag=True, mv_flag=True):
    pr_file_name = f"{target_row['ID']}-{target_row['NAME']}-PR.jmfit"
    mv_file_name = f"{target_row['ID']}-{target_row['NAME']}-MV.jmfit"
    summary_df = pd.DataFrame(columns=['MODE', 'PEAK', 'PEAK_ERR', 'SNR', 'RMS', 'RA', 'RA_ERR', 'DEC', 'DEC_ERR',
                                       'MAJOR', 'MAJOR_ERR', 'MINOR', 'MINOR_ERR', 'PA', 'PA_ERR'])
    summary_df.loc[0, 'MODE'] = 'PR'
    summary_df.loc[1, 'MODE'] = 'MV'

    if pr_flag:
        with open(os.path.join(exp_dir, pr_file_name), 'r', encoding='utf-8') as file:
            for line in file:
                pattern = re.compile(r'Solution RMS\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*in\d+\s*usable pixels')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'RMS'] = float(match.group(1))
                    continue
                pattern = re.compile(r'Peak intensity\s*=\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*\+/-\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*JY/BEAM\s*\(\s*(\d+\.\d+)\s*\)')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'PEAK'] = float(match.group(1))
                    summary_df.loc[0, 'PEAK_ERR'] = float(match.group(3))
                    summary_df.loc[0, 'SNR'] = float(match.group(5))
                    continue
                pattern = re.compile(r'RA\s+(\d+\s+\d+\s+\d+.\d+)\s+\+/-\s+(\d+.\d+)')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'RA'] = match.group(1)
                    summary_df.loc[0, 'RA_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'DEC\s+([+-]?\d+\s+\d+\s+\d+.\d+)\s+\+/-\s+(\d+.\d+)')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'DEC'] = match.group(1)
                    summary_df.loc[0, 'DEC_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'Major axis\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+asec')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'MAJOR'] = float(match.group(1))
                    summary_df.loc[0, 'MAJOR_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'Minor axis\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+asec')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'MINOR'] = float(match.group(1))
                    summary_df.loc[0, 'MINOR_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'Position angle\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+degrees')
                match = pattern.search(line)
                if match:
                    summary_df.loc[0, 'PA'] = float(match.group(1))
                    summary_df.loc[0, 'PA_ERR'] = float(match.group(2))
                    continue

    if mv_flag:
        with open(os.path.join(exp_dir, mv_file_name), 'r', encoding='utf-8') as file:
            for line in file:
                pattern = re.compile(r'Solution RMS\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*in\d+\s*usable pixels')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'RMS'] = float(match.group(1))
                    continue
                pattern = re.compile(r'Peak intensity\s*=\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*\+/-\s*([+-]?\d+(\.\d+)?[eE][+-]?\d+)\s*JY/BEAM\s*\(\s*(\d+\.\d+)\s*\)')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'PEAK'] = float(match.group(1))
                    summary_df.loc[1, 'PEAK_ERR'] = float(match.group(3))
                    summary_df.loc[1, 'SNR'] = float(match.group(5))
                    continue
                pattern = re.compile(r'RA\s+(\d+\s+\d+\s+\d+.\d+)\s+\+/-\s+(\d+.\d+)')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'RA'] = match.group(1)
                    summary_df.loc[1, 'RA_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'DEC\s+([+-]?\d+\s+\d+\s+\d+.\d+)\s+\+/-\s+(\d+.\d+)')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'DEC'] = match.group(1)
                    summary_df.loc[1, 'DEC_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'Major axis\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+asec')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'MAJOR'] = float(match.group(1))
                    summary_df.loc[1, 'MAJOR_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'Minor axis\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+asec')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'MINOR'] = float(match.group(1))
                    summary_df.loc[1, 'MINOR_ERR'] = float(match.group(2))
                    continue
                pattern = re.compile(r'Position angle\s+=\s+(\d+.\d+)\s+\+/-\s+(\d+.\d+)\s+degrees')
                match = pattern.search(line)
                if match:
                    summary_df.loc[1, 'PA'] = float(match.group(1))
                    summary_df.loc[1, 'PA_ERR'] = float(match.group(2))
                    continue

    if pr_flag or mv_flag:
        summary_file_name = os.path.join(exp_dir, f"{target_row['ID']}-{target_row['NAME']}-SUMMARY.csv")
        summary_df.to_csv(summary_file_name, index=False)
