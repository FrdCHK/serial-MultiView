"""
class for calibrators
@Author: Jingdong Zhang
@DATE  : 2024/7/17
"""
from astropy.coordinates import SkyCoord
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
        this_coord = SkyCoord(self.ra, self.dec, unit=u.deg, frame='icrs')
        pri_coord = SkyCoord(pri_ra, pri_dec, unit=u.deg, frame='icrs')
        dx, dy = this_coord.spherical_offsets_to(pri_coord)
        self.dx = dx.deg
        self.dy = dy.deg
