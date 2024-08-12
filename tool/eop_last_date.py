"""
extract last date from eop file
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
import re


def eop_last_date(file_path):
    date_pattern = re.compile(r'# Last date with real data:\s+(\d{4}\.\d{2}\.\d{2})')

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = date_pattern.search(line)
            if match:
                return match.group(1)

    return None


if __name__ == "__main__":
    pass
