"""
convert cartesian coordinates to spherical coordinates
@Author: Jingdong Zhang
@DATE  : 2024/9/9
"""
import numpy as np


def cartesian_to_spherical(x, y, z):
    """
    convert cartesian coordinates (unit vector) to spherical coordinates (r=1)
    :param x: x component of cartesian coordinates
    :param y: y component of cartesian coordinates
    :param z: z component of cartesian coordinates
    :return: spherical coordinates theta, phi
    """
    # r = 1 for unit vector, so we directly calculate theta and phi
    theta = np.arccos(z)  # Since r is 1, we use z directly
    phi = np.arctan2(y, x)  # atan2 gives the correct quadrant for the angle
    return theta, phi
