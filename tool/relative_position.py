"""
description
@Author: Jingdong Zhang
@DATE  : 2024/7/26
"""
from astropy.coordinates import Angle
from astropy import units as u


def relative_position(reference_pos, target_pos):
    """
    Calculate the position of target relative to reference position
    :param reference_pos: reference position, unit: deg
    :param target_pos: target position, unit: deg
    :return: [delta ra, delta dec], unit: deg
    """
    ref_ra, ref_dec = reference_pos
    target_ra, target_dec = target_pos
    lon = Angle(target_ra, unit=u.deg)
    lat = Angle(target_dec, unit=u.deg)
    lon_pri = Angle(ref_ra, unit=u.deg)
    lat_pri = Angle(ref_dec, unit=u.deg)
    ref_lon = lon - lon_pri
    ref_lat = lat - lat_pri
    dx = ref_lon.deg
    dy = ref_lat.deg
    return [dx, dy]
