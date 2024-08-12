"""
handling user input (float)
@Author: Jingdong Zhang
@DATE  : 2024/7/3
"""
import tool


def float_input(prompt, default=None):
    while True:
        prompt_str = prompt
        if default is not None:
            prompt_str += f"({default:<f})"
        prompt_str += ':'
        user_input = input(prompt_str)
        if (default is not None) and (user_input == ''):
            return default
        elif tool.is_float(user_input):
            return float(user_input)
        else:
            print("\033[31mInvalid input!\033[0m")
