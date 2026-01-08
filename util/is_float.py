"""
determine whether input is an integer
@Author: Jingdong Zhang
@DATE  : 2024/7/3
"""


def is_float(user_input):
    try:
        float(user_input)
        return True
    except ValueError:
        return False
