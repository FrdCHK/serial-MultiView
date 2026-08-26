import argparse
import copy
import yaml
from jinja2 import Environment, FileSystemLoader

from core.solver_config_compat import migrate_legacy_solver_config
from util.path_input import path_input


def render_control(template_path, config):
    """Render one control file after migrating legacy public solver keys."""

    render_config = copy.deepcopy(config or {})
    migrate_legacy_solver_config(render_config)
    env = Environment(loader=FileSystemLoader('.'), trim_blocks=True)
    template = env.get_template(template_path)
    return template.render(**render_config, config=render_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=str, help="jinja template file name")
    parser.add_argument("--config", type=str, help="input config file path")
    parser.add_argument("--control", type=str, help="output control file path")
    args = parser.parse_args()
    if args.template is None:
        args.template = path_input("Please specify jinja template file (root dir is ./template)", "file", exist=True)
    if args.config is None:
        args.config = path_input("Please specify input config file path", "file", exist=True)
    if args.control is None:
        args.control = path_input("Please specify output control file path", "file")

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    control = render_control(args.template, config)
    with open(args.control, 'w') as file:
        file.write(control)
    print(f"Success: control file written to {args.control}")
