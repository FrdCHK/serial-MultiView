import os
from jinja2 import Environment, FileSystemLoader
import subprocess

from core.Plugin import Plugin
from core.Context import Context


class Difmap(Plugin):
    @classmethod
    def get_description(cls) -> str:
        return "Call difmap to clean and self calibrate the calibrator maps."
    
    def run(self, context: Context) -> bool:
        # TODO : add adjustable parameters from config
        context.logger.info(f"Start calibrator self-calibration")

        env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))), trim_blocks=True, keep_trailing_newline=True)

        template = env.get_template("difmap_commands.par.j2")
        workspace_dir = context.get_context()["config"]["workspace"]
        targets_dir = os.path.join(workspace_dir, "targets")
        try:
            # pgplot cannot accept long path, so create a temp link to the targets directory
            pg_link = "pg_link"
            if not os.path.exists(pg_link):
                os.symlink(targets_dir, pg_link)
            elif os.path.exists(pg_link) and (not os.path.islink(pg_link)):
                context.logger.error(f"Failed to create symlink for PGPLOT: {pg_link} already exists and is not a symlink")
                return False
            for target in context.get_context().get("targets"):
                target_dir = os.path.join(pg_link, target["NAME"])
                calibrator_dir = os.path.join(target_dir, "calibrators")
                for calibrator in target["CALIBRATORS"]:
                    config = {"uv_file": os.path.join(calibrator_dir, f"{calibrator['NAME']}_FITTP.fits"),
                            "IF_end": context.get_context()["no_if"],
                            "save_file_prefix": os.path.join(calibrator_dir, f"{calibrator['NAME']}_selfcal")}
                    par = template.render(**config)
                    par_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "difmap_commands.par")
                    with open(par_path, 'w') as file:
                        file.write(par)
                    self.run_difmap(par_path)
                    os.remove(par_path)
        except Exception as e:
            context.logger.info(f"Error in calibrator self-calibration: {e}")
            return False
        finally:
            if os.path.islink(pg_link):
                os.remove(pg_link)
            for filename in os.listdir(os.getcwd()):
                if filename.startswith("difmap.log"):
                    os.remove(os.path.join(os.getcwd(), filename))

        context.logger.info(f"Calibrator self-calibration finished")
        return True

    @staticmethod
    def run_difmap(par_path):
        subprocess.run(["difmap"],
                       stdin=open(par_path),
                    #    stdout=subprocess.DEVNULL,
                    #    stderr=subprocess.DEVNULL,
                       check=True)
