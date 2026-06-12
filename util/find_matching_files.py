"""
find matching files in given directory
@Author: Jingdong Zhang
@DATE  : 2024/9/19
"""
import re
import os


def find_matching_files(directory, prefix='', suffix='CONF', ext='yaml'):
    pattern = re.compile(
        rf'^{re.escape(prefix)}-(\d+)-(.+?)-{re.escape(suffix)}\.{re.escape(ext)}$'
    )
    matching_files = []
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            file_id = match.group(1)
            name = match.group(2)
            matching_files.append((filename, int(file_id), name))
    return matching_files
