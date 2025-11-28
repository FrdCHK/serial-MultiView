from core.Context import Context

def check_plugin_availability(context: Context) -> bool:
    context.logger.info("Start checking availabiliy of all plugins in the list")
    availability_flag = True
    for item in context.get_context().get("plugins", {}):
        if item['name'] not in context.get_context().get("loaded_plugins"):
            context.logger.error(f"Plugin {item['name']} is not available")
            availability_flag = False
    if availability_flag:
        context.logger.info(f"All plugins are available")
        return True
    else:
        return False
