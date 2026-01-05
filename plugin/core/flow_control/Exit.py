from core.Plugin import Plugin
from core.Context import Context


class Exit(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Save context and exit."

    def run(self, context: Context) -> bool:
        if context.get_context()["context_file_path"] is not None:
            context.save_context_to_file()
        context.logger.info("Exit")
        return True
