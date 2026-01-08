from AIPSTask import AIPSTask
from typing import Dict, Any

from core.Context import Context
from util.parse_context_variable import parse_context_variable

def run_task(task: AIPSTask, params: Dict[str, Any], context: Context) -> bool:
    try:
        resolved = parse_context_variable(params, context)
    except KeyError as e:
        context.logger.error(e)
        return False
    for _, param_value in resolved.items():
        if isinstance(param_value, list):
            param_value.insert(0, None)
    
    task_attributes = [attr for attr in dir(task) if not attr.startswith('_')]
    for param_key, param_value in resolved.items():
        if param_key in task_attributes:
            # Check if it's a callable method or an attribute
            attr = getattr(task, param_key)
            if callable(attr):
                # It's a method, call it with the parameter value
                attr(param_value)
            else:
                # It's an attribute, set its value
                setattr(task, param_key, param_value)
    try:
        task.go()
    except Exception as e:
        context.logger.error(f"Error in AIPS task run: {e}")
        return False
    else:
        return True
