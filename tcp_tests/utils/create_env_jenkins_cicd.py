#!/usr/bin/env python

import os
import sys

sys.path.append(os.getcwd())
try:
    from tcp_tests.fixtures import config_fixtures
    from tcp_tests.managers import underlay_ssh_manager
    from tcp_tests.managers import saltmanager as salt_manager
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)


def main():
    tests_configs = os.environ.get('TESTS_CONFIGS', None)
    if not tests_configs or not os.path.isfile(tests_configs):
        print("Please set TESTS_CONFIGS environment variable whith"
              "the path to INI file with lab metadata.")
        return 1
    config = config_fixtures.config()
    underlay = underlay_ssh_manager.UnderlaySSHManager(config)
    saltmanager = salt_manager.SaltManager(config, underlay)
    saltmanager.create_env_jenkins_cicd()
    saltmanager.create_env_k8s()


if __name__ == '__main__':
    sys.exit(main())
