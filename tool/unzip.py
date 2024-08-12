"""
unzip ionex file
@Author: Jingdong Zhang
@DATE  : 2024/7/2
"""
import os
import sys


def unzip(source):
    try:
        os.system(f'gunzip {source}')
    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    pass
