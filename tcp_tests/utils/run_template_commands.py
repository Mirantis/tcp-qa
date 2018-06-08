#!/usr/bin/env python

import argparse
import os
import sys

sys.path.append(os.getcwd())
try:
    from tcp_tests.helpers import ext
    from tcp_tests.fixtures import config_fixtures
    from tcp_tests.managers import underlay_ssh_manager
    from tcp_tests.managers import execute_commands
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)


def load_params():
    """
    Parse CLI arguments and environment variables

    Returns: ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description=(
        'Run commands from yaml templates'
    ))
    parser.add_argument('path_to_template',
                        help='Path to YAML template')
    parser.add_argument('--template-steps-label',
                        help=('Text that will be shown as steps label'),
                        default='',
                        type=str)

    return parser


def main():
    """Create fuel-devops environment from template"""
    parser = load_params()
    opts = parser.parse_args()

    if opts.path_to_template is None:
        parser.print_help()
        return 10

    path = os.path.abspath(opts.path_to_template)
    label = opts.template_steps_label
    if not label:
        label = os.path.basename(path).split('.')[0]

    config = config_fixtures.config()
    underlay = underlay_ssh_manager.UnderlaySSHManager(config)

    commands = underlay.read_template(path)

    commander = execute_commands.ExecuteCommandsMixin(config, underlay)
    commander.execute_commands(commands, label=label)


if __name__ == '__main__':
    sys.exit(main())
