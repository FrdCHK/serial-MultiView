import argparse

from core.logger_init import logger_init
from core.Context import Context
from core.plugin_load import plugin_load
from util.check_plugin_availability import check_plugin_availability

from util.path_input import path_input


def main(config: str, log: str) -> None:
    logger = logger_init(log)
    logger.info("Start main")

    context = Context(logger, config)
    if not context.get_context():
        logger.error("Terminate main")
        return
    context.edit_context({"config_path": config})
    context.edit_context({"log_dir": log})
    context.edit_context({"logger": logger})
    logger.info("Initiating context succeeded")

    plugins = plugin_load("plugin", logger)
    context.edit_context({"loaded_plugins": plugins})
    if not check_plugin_availability(context):
        logger.error("Terminate main: error in plugin availability check")
        return
    for item in context.get_context().get("plugins", {}):
        if item['name'] in plugins:
            plugin_instance = plugins[item['name']](item['params'])
            if not plugin_instance.run(context):
                logger.error(f"Terminate main: error in plugin {item['name']}")
                return

    logger.info("End main")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=str, help="control file path")
    parser.add_argument("--log", type=str, help="log file directory", default="log")
    args = parser.parse_args()
    if args.control is None:
        args.control = path_input("Please specify control file path", "file", exist=True)
    main(args.control, args.log)
