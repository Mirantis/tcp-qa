#!/usr/bin/env python

import os
import sys

sys.path.append(os.getcwd())
try:
    from tcp_tests.managers.saltmanager import SaltManager
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)


def main():
    saltmanager = SaltManager
    saltmanager.create_env_jenkins_cicd()
    saltmanager.create_env_k8s()


if __name__ == '__main__':
    sys.exit(main())
