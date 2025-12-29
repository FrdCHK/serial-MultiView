"""
handling user input (integer)
@Author: Jingdong Zhang
@DATE  : 2024/7/3
"""
from .is_integer import is_integer


def integer_input(prompt: str, default: int=None):
    while True:
        prompt_str = prompt
        if default is not None:
            prompt_str += f" ({default:<d})"
        prompt_str += ': '
        user_input = input(prompt_str)
        if (default is not None) and (user_input == ''):
            return default
        elif is_integer(user_input):
            return int(user_input)
        else:
            print("\033[31mInvalid input!\033[0m")
