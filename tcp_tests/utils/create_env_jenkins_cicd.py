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
    config = config_fixtures.config()
    underlay = underlay_ssh_manager.UnderlaySSHManager(config)
    saltmanager = salt_manager.SaltManager(config, underlay)
    saltmanager.create_env_jenkins_cicd()
    saltmanager.create_env_k8s()


if __name__ == '__main__':
    sys.exit(main())
