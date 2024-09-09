"""
give a predicted normal vector according to previous time series slice
@Author: Jingdong Zhang
@DATE  : 2024/9/9
"""
import numpy as np
from scipy.interpolate import UnivariateSpline
from astropy.coordinates import Angle
import astropy.units as u

import tool


def predict(data, predict_time):
    time_series = data[:, 0]
    vectors = data[:, 1:]

    sphere = []
    for i in range(vectors.shape[0]):
        t, p = tool.cartesian_to_spherical(vectors[i, 0], vectors[i, 1], vectors[i, 2])
        sphere.append([t, p])
    sphere = np.array(sphere)

    spline_t = UnivariateSpline(time_series, sphere[:, 0], k=1, ext=0)
    spline_p = UnivariateSpline(time_series, sphere[:, 1], k=1, ext=0)

    # 预测给定时间点的向量
    t = spline_t(predict_time)
    p = spline_p(predict_time)
    t = Angle(t, unit=u.rad).wrap_at(np.pi * u.rad)
    p = Angle(p, unit=u.rad).wrap_at(2 * np.pi * u.rad)
    x, y, z = np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)
    predicted_vector = np.array([x, y, z])[:, np.newaxis]

    # 归一化，确保仍是单位向量
    predicted_vector /= np.linalg.norm(predicted_vector)

    return predicted_vector
