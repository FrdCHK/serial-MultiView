import os

from core.Plugin import Plugin
from core.Context import Context


class CreateDirectories(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "create directories in workspace"

    def run(self, context: Context) -> bool:
        context.logger.info("Start creating directories in workspace")
        directory_tree = context.get_context().get("directory_tree", {})
        if not directory_tree:
            workspace_dir = os.path.dirname(context.get_context()["config_path"])
            directory_tree.update({"directory": workspace_dir, "sub_directories": []})
            target_dir = os.path.join(workspace_dir, "target")
            os.makedirs(target_dir, exist_ok=True)
            directory_tree["sub_directories"].append({"directory": target_dir, "sub_directories": []})
            context.logger.info("Created target directory (or already exists)")
            context.edit_context({"directory_tree": directory_tree})
            return True
        else:
            # TODO: create sub directories for targets. waiting for read data module to init context.
            return True
