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
    """
    predict next normal vector according to previous time series slice
    :param data: previous time series slice
    :param predict_time: the time to be predicted
    :return: predicted normal vector at given time
    """
    time_series = data[:, 0]
    vectors = data[:, 1:]

    sphere = []
    for i in range(vectors.shape[0]):
        t, p = tool.cartesian_to_spherical(vectors[i, 0], vectors[i, 1], vectors[i, 2])
        # convert phi to sin & cos to avoid jump close to 2pi
        sin_phi = np.sin(p)
        cos_phi = np.cos(p)
        sphere.append([t, sin_phi, cos_phi])
    sphere = np.array(sphere)

    # spline extrapolation
    # spline_t = UnivariateSpline(time_series, sphere[:, 0], k=1, ext=0)
    # sin_spline_p = UnivariateSpline(time_series, sphere[:, 1], k=1, ext=0)
    # cos_spline_p = UnivariateSpline(time_series, sphere[:, 2], k=1, ext=0)
    # t = spline_t(predict_time)
    # sin_p = sin_spline_p(predict_time)
    # cos_p = cos_spline_p(predict_time)

    # linear polyfit extrapolation with last four points
    last = sphere[-4:, 0]
    coef = np.polyfit(time_series[-4:], last, 1)
    linear_extrapolation = np.poly1d(coef)
    t = linear_extrapolation(predict_time)
    last = sphere[-4:, 1]
    coef = np.polyfit(time_series[-4:], last, 1)
    linear_extrapolation = np.poly1d(coef)
    sin_p = linear_extrapolation(predict_time)
    last = sphere[-4:, 2]
    coef = np.polyfit(time_series[-4:], last, 1)
    linear_extrapolation = np.poly1d(coef)
    cos_p = linear_extrapolation(predict_time)

    p = np.arctan2(sin_p, cos_p)
    t = Angle(t, unit=u.rad).wrap_at(np.pi * u.rad)
    p = Angle(p, unit=u.rad).wrap_at(2 * np.pi * u.rad)
    x, y, z = np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)
    predicted_vector = np.array([x, y, z])[:, np.newaxis]

    # normalize
    predicted_vector /= np.linalg.norm(predicted_vector)

    return predicted_vector
