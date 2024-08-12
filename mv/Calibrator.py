"""
class for calibrators
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""
from astropy.coordinates import Angle
from astropy import units as u


class Calibrator:
    def __init__(self, source_id, name, ra, dec, sn_id, sn_table):
        self.id = source_id
        self.name = name
        self.ra = ra
        self.dec = dec
        self.sn_id = sn_id
        self.sn_table = sn_table
        self.dx = 0.
        self.dy = 0.

    def calc_relative_position(self, pri_ra, pri_dec):
        lon = Angle(self.ra, unit=u.deg)
        lat = Angle(self.dec, unit=u.deg)
        lon_pri = Angle(pri_ra, unit=u.deg)
        lat_pri = Angle(pri_dec, unit=u.deg)
        ref_lon = lon - lon_pri
        ref_lat = lat - lat_pri
        self.dx = ref_lon.deg
        self.dy = ref_lat.deg
