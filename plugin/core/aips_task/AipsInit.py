from AIPS import AIPS

from core.Plugin import Plugin
from core.Context import Context


class AipsInit(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Set AIPS userno."
    
    def run(self, context: Context) -> bool:
        aips_userno = self.params.get("userno", 1)
        AIPS.userno = aips_userno
        context.edit_context({"aips_userno": aips_userno})
        context.logger.info(f"AIPS userno set to {aips_userno}")
        return True
