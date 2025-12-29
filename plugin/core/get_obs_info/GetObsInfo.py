from typing import Dict, Any
from AIPSData import AIPSUVData
import pandas as pd
from datetime import datetime
from astropy.time import Time

from core.Plugin import Plugin
from core.Context import Context
from util.float_to_time_components import float_to_time_components


class GetObsInfo(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """inname, inclass, inseq, and indisk must be specified; optional: listr_outprint, listr_optype, prtan_outprint"""
        self.params = params

    @classmethod
    def get_description(cls) -> str:
        return "Get observation information from catalog. Plugin required: GeneralTask."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start reading observation information from catalog")
        data = AIPSUVData(self.params["inname"], self.params["inclass"], int(self.params["indisk"]), int(self.params["inseq"]))
        antennas = data.antennas
        antennas = pd.DataFrame({"ID": range(1, len(antennas) + 1), "NAME": antennas})

        su_table = data.table('AIPS SU', 0)
        sources = pd.DataFrame(columns=["ID", "NAME", "RA", "DEC"])
        for su_item in su_table:
            sources.loc[sources.index.size] = [su_item["id__no"], su_item["source"].rstrip(),
                                            su_item["raepo"], su_item["decepo"]]

        obs_date = data.header.date_obs
        obs_date = datetime.strptime(obs_date, "%Y-%m-%d")
        jd_0 = Time(obs_date).jd  # julian day
        obs_year = obs_date.year  # obs year
        obs_doy = obs_date.timetuple().tm_yday  # day of year (first day of obs)
        nx_table = data.table('AIPS NX', 0)
        nx_df = pd.DataFrame(columns=["time", "time_interval", "source_id"])
        for item in nx_table:
            nx_df.loc[nx_df.index.size] = [item["time"], item["time_interval"], item["source_id"]]
        obs_day_num = int(nx_table[len(nx_table) - 1]['time'] + 1)  # obs day number

        obs_freq = data.header.crval[2] * 1e-9  # obs frequency in GHz
        no_stokes = data.header.naxis[1]  # polarization number
        no_if = data.header.naxis[3]  # IF number
        no_chan = data.header.naxis[2]  # channel number per IF

        fringe_finder_name = sources.loc[sources['ID'] == nx_table[0]['source_id'], 'NAME'].values[0].rstrip()
        # NOTE AIPS timerange: the data points (~2 sec each usually) in a scan are not integrated, so, cover the whole scan!
        first_scan_end_time = nx_table[0]['time']+nx_table[0]['time_interval']/2+1e-3  # add extra ~1 min (unit: d)
        end_day, end_hour, end_minute, end_second = float_to_time_components(first_scan_end_time)

        context.edit_context({"antennas": antennas.to_dict(orient='records'),
                              "sources": sources.to_dict(orient='records'),
                              "obs_time": {"date": obs_date,
                                           "jd_0": float(jd_0),
                                           "year": obs_year,
                                           "doy": obs_doy,
                                           "day_num": obs_day_num},
                              "obs_freq": obs_freq,
                              "no_stokes": no_stokes,
                              "no_if": no_if,
                              "no_chan": no_chan,
                              "mpc_calsour": {"name": fringe_finder_name,
                                              "end_time": {"day": end_day,
                                                           "hour": end_hour,
                                                           "minute": end_minute,
                                                           "second": end_second}}})
        
        # optional: LISTR & PRTAN
        if (("listr_outprint" in self.params) or ("prtan_outprint" in self.params)) and ("GeneralTask" not in context.get_context()["loaded_plugins"]):
            context.logger.error("Plugin GeneralTask not found")
            return False
        if "listr_outprint" in self.params:
            task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "LISTR",
                                                                           "inname": self.params["inname"],
                                                                           "inclass": self.params["inclass"],
                                                                           "indisk": self.params["indisk"],
                                                                           "inseq": self.params["inseq"],
                                                                           "optype": self.params["listr_optype"] if "listr_optype" in self.params else "SCAN",
                                                                           "docrt": -1,
                                                                           "outprint": self.params["listr_outprint"]})
            task.run(context)
        if "prtan_outprint" in self.params:
            task = context.get_context()["loaded_plugins"]["GeneralTask"]({"task_name": "PRTAN",
                                                                           "inname": self.params["inname"],
                                                                           "inclass": self.params["inclass"],
                                                                           "indisk": self.params["indisk"],
                                                                           "inseq": self.params["inseq"],
                                                                           "docrt": -1,
                                                                           "outprint": self.params["prtan_outprint"]})
            task.run(context)
        
        context.logger.info(f"Observation information has been read from catalog")
        return True
