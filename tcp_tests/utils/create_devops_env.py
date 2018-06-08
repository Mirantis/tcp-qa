#!/usr/bin/env python

import os
import sys

sys.path.append(os.getcwd())
try:
    from tcp_tests.helpers import ext
    from tcp_tests.fixtures import config_fixtures
    from tcp_tests.managers import envmanager_devops
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)


def main():
    """Create fuel-devops environment from template"""
    config = config_fixtures.config()
    env = envmanager_devops.EnvironmentManager(config=config)
    if not env.has_snapshot(ext.SNAPSHOT.hardware):
        env.create_snapshot(ext.SNAPSHOT.hardware)


if __name__ == '__main__':
    sys.exit(main())
