import argparse
import yaml
from jinja2 import Environment, FileSystemLoader

from util.path_input import path_input


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

    env = Environment(loader=FileSystemLoader('./template'), trim_blocks=True)

    template = env.get_template(args.template)

    with open(args.config, 'r') as file:
        paras = yaml.safe_load(file)

    control = template.render(paras)
    with open(args.control, 'w') as file:
        file.write(control)
    print(f"Control file written to {args.control}")
