"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/18
"""
import numpy as np

import mv


def rodrigues_rotation(norm_vec, new_point):
    """
    normal vector rotation algorithm based on Rodrigues' rotation formula
    rotate the plane to make it cross point new_point
    the rotation angle is minimum
    :param norm_vec: normal vector to be rotated
    :param new_point: the new point that the plane will cross
    :return: the rotated normal vector, rotation axis, rotation angle
    """
    vertical_proj = mv.plane(*norm_vec, new_point[0], new_point[1])
    symbol_sin = mv.symbol(vertical_proj, new_point[2])
    point_norm_vec = np.array([[new_point[0]], [new_point[1]], [new_point[2]]])
    k = np.cross(norm_vec, point_norm_vec, axisa=0, axisb=0).T
    k = k/np.linalg.norm(k)
    p = np.cross(k, norm_vec, axisa=0, axisb=0).T
    cos_theta = np.dot(point_norm_vec.T, p)[0, 0]/(np.linalg.norm(point_norm_vec)*np.linalg.norm(p))
    if cos_theta > 1:
        cos_theta = 1.
    sin_theta = np.sqrt(1-cos_theta**2)*symbol_sin
    return (norm_vec + (1-cos_theta) * np.cross(k, np.cross(k, norm_vec, axisa=0, axisb=0).T, axisa=0, axisb=0).T +
            sin_theta * np.cross(k, norm_vec, axisa=0, axisb=0).T, k, np.arcsin(sin_theta))
