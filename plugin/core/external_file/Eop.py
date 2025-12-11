from datetime import datetime, timedelta
import re
import pycurl
import os

from core.Plugin import Plugin
from core.Context import Context


class Eop(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Check EOP file availability. Download EOP file if not available. A parameter eop_path is required."
    
    def run(self, context: Context) -> bool:
        context.logger.info("Start EOP file preparation")

        try:
            eop_try_open = open(self.params["eop_path"], "r")
        except IOError:
            context.logger.info("EOP file needs to be downloaded")
            self.eop_download(context)
        else:
            eop_try_open.close()
            current_eop_last_date = self.eop_last_date(context)
            # AIPS requires real data in EOP file cover obs_date+3
            obs_last_date = context.get_context()["obs_time"]["date"] + timedelta(days=(context.get_context()["obs_time"]["day_num"]-1+3))
            if current_eop_last_date < obs_last_date:
                context.logger.info("EOP file needs to be updated")
                os.remove(self.params["eop_path"])
                self.eop_download(context)
            else:
                context.logger.info("Current EOP file is OK")

        context.logger.info("EOP file preparation finished")
        return True
    
    def eop_last_date(self, context: Context) -> datetime:
        """
        Check the last date with real data in current EOP file
        
        :param context: context instance
        :type context: Context
        :return: the last date with real data
        :rtype: datetime
        """
        date_pattern = re.compile(r'# Last date with real data:\s+(\d{4}\.\d{2}\.\d{2})')
        try:
            eop_try_open = open(self.params["eop_path"], 'r', encoding='utf-8')
        except IOError:
            context.logger.error(f"EOP file does not exist")
            return None
        else:
            for line in eop_try_open:
                match = date_pattern.search(line)
                if match:
                    # return match.group(1)
                    return datetime.strptime(match.group(1), "%Y.%m.%d")
            context.logger.error(f"This is not a standard EOP file")
            return None

    def eop_download(self, context: Context) -> bool:
        """
        Download EOP file to a given path
        
        :param context: context instance
        :type context: Context
        :return: whether download is successful
        :rtype: bool
        """
        with open(self.params["eop_path"], 'wb') as f:
            c = pycurl.Curl()
            c.setopt(c.URL, "ftp://gdc.cddis.eosdis.nasa.gov/vlbi/gsfc/ancillary/solve_apriori/usno_finals.erp")
            c.setopt(c.USERPWD, "anonymous:daip@nrao.edu")
            c.setopt(c.FTP_SSL, pycurl.FTPSSL_ALL)
            c.setopt(c.WRITEDATA, f)
            c.perform()
            c.close()
        try:
            eop_try_open = open(self.params["eop_path"], "r")
        except IOError:
            context.logger.error(f"EOP file download failed")
            return False
        else:
            eop_try_open.close()
            context.logger.info("EOP file downloaded")
            return True
