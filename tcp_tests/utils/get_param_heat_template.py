#!/usr/bin/env python

import os
import sys

from heatclient.common import template_utils


if len(sys.argv) <= 1:
    print("Usage:\n"
          "  export LAB_CONFIG_NAME=cookied-cicd-...  "
          "# see directories in tcp_tests/templates/\n"
          "  export LAB_PARAM_DEFAULTS=nnnn.env "
          "# see files in tcp_tests/templates/_heat_environments")
    sys.exit(1)

sys.path.append(os.getcwd())
try:
    from tcp_tests import settings_oslo
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)

config = settings_oslo.load_config([])

template_file = config.hardware.heat_conf_path
env_file = config.hardware.heat_env_path

if not os.path.exists(template_file):
    raise Exception("Heat template '{0}' not found!\n"
                    "Please set the correct LAB_CONFIG_NAME with underlay.hot"
                    .format(template_file))

tpl_files, template = template_utils.get_template_contents(
    template_file)

if os.path.exists(env_file):
    env_files_list = []
    env_files, env = (
        template_utils.process_multiple_environments_and_files(
            env_paths=[env_file],
            env_list_tracker=env_files_list))
else:
    env = {}

parameter_name = sys.argv[1]
parameter_value = env['parameter_defaults'].get(parameter_name)
if parameter_value is None:
    parameter_template = template['parameters'].get(parameter_name,{})
    parameter_value = parameter_template.get('default')
    if parameter_value is None:
        raise Exception("Parameter '{0}' not found in env file '{1}' "
                        "and temlate file '{2}'"
                        .format(parameter_name, env_file, template_file))

print(parameter_value)
