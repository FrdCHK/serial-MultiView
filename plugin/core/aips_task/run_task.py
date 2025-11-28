from AIPSTask import AIPSTask
from typing import Dict, Any

def run_task(task: AIPSTask, params: Dict[str, Any]) -> None:
    task_attributes = [attr for attr in dir(task) if not attr.startswith('_')]
    for param_key, param_value in params.items():
        if param_key in task_attributes:
            # Check if it's a callable method or an attribute
            attr = getattr(task, param_key)
            if callable(attr):
                # It's a method, call it with the parameter value
                attr(param_value)
            else:
                # It's an attribute, set its value
                setattr(task, param_key, param_value)
    task.go()
