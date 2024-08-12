"""
plane function
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""


def plane(a, b, c, x, y):
    """
    calculate z on a plane at (x, y)
    :param a: normal vector X
    :param b: normal vector Y
    :param c: normal vector Z
    :param x: position x
    :param y: position y
    :return: z value
    """
    return (a*x + b*y) / (-c)
