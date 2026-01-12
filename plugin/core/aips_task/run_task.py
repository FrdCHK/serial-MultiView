import os
from AIPSTask import AIPSTask
from typing import Dict, Any

from core.Context import Context
from util.parse_context_variable import parse_context_variable
from util.create_short_link import create_short_link

def run_task(task: AIPSTask, params: Dict[str, Any], context: Context) -> bool:
    try:
        resolved = parse_context_variable(params, context)
    except KeyError as e:
        context.logger.error(e)
        return False
    output_name_pairs = []
    temp_links = []
    for param_key, param_value in resolved.items():
        if isinstance(param_value, list):
            param_value.insert(0, None)
        if param_key in ["datain", "dataout", "infile", "fitout"] and isinstance(param_value, str) and len(param_value) > 47:
            actual_path = param_value
            parent_link, temp_path = create_short_link(param_value)
            context.logger.debug(f"Path too long for AIPS, creating temp symlink {parent_link}")
            temp_links.append(parent_link)
            if param_key in ["dataout", "fitout"]:
                _, ext = os.path.splitext(actual_path)
                output_name_pairs.append({"final_name": actual_path, "temp_name": os.path.join(os.path.dirname(actual_path), f"temp{ext}")})
                resolved[param_key] = os.path.join(parent_link, f"temp{ext}")
            else:
                resolved[param_key] = temp_path
    
    try:
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
        task.go()
    except Exception as e:
        context.logger.error(f"Error in AIPS task run: {e}")
        return False
    else:
        return True
    finally:
        for pairs in output_name_pairs:
            context.logger.debug(f"Renaming {pairs['temp_name']} to {pairs['final_name']}")
            os.rename(pairs['temp_name'], pairs['final_name'])
        for temp_link in temp_links:
            context.logger.debug(f"Removing temp symlink: {temp_link}")
            os.remove(temp_link)
