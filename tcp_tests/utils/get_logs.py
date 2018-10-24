#!/usr/bin/env python

import argparse
import os
import sys
import time

sys.path.append(os.getcwd())
try:
    from tcp_tests.fixtures import config_fixtures
    from tcp_tests.managers import underlay_ssh_manager
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
        'Download logs and debug info from salt minions'
    ))
    default_name_prefix = 'logs_' + time.strftime("%Y%m%d_%H%M%S")
    parser.add_argument('--archive-name-prefix',
                        help=('Custom prefix for creating archive name'),
                        default=default_name_prefix,
                        type=str)
    return parser


def main():
    parser = load_params()
    opts = parser.parse_args()

    tests_configs = os.environ.get('TESTS_CONFIGS', None)
    if not tests_configs or not os.path.isfile(tests_configs):
        print("Download logs and debug info from salt minions. "
              "Please set TESTS_CONFIGS environment variable whith"
              "the path to INI file with lab metadata.")
        return 11

    config = config_fixtures.config()
    underlay = underlay_ssh_manager.UnderlaySSHManager(config)

    underlay.get_logs(opts.archive_name_prefix)

if __name__ == '__main__':
    sys.exit(main())
