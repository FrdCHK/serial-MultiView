from typing import Dict, Any
from AIPSTask import AIPSTask

from core.Plugin import Plugin
from core.Context import Context

from .run_task import run_task


class GeneralTask(Plugin):
    def __init__(self, params: Dict[str, Any]):
        """task_name must be specified"""
        self.params = {k: v for k, v in params.items() if k != "task_name"}
        self.task_name = params["task_name"]
        for _, v in self.params.items():
            if isinstance(v, list):
                v.insert(0, None)
        self.task = AIPSTask(self.task_name)

    @classmethod
    def get_description(cls) -> str:
        return "A general task class."
    
    def run(self, context: Context) -> bool:
        context.logger.info(f"Start AIPS task {self.task_name}")
        run_task(self.task, self.params)
        context.logger.info(f"AIPS task {self.task_name} finished")
        return True
