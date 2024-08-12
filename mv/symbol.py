"""
symbol function
@Author: Jingdong Zhang
@DATE  : 2024/7/18
"""


def symbol(proj, z):
    """
    to judge the symbol of sin
    :param proj: z value of vertical projection of the new point onto the plane
    :param z: z value of the new point
    :return: symbol of sin, 1 or -1
    """
    if proj >= z:
        return 1
    else:
        return -1
