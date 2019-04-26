#!/usr/bin/env python
#    Copyright 2017 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import os
import sys

sys.path.append(os.getcwd())
try:
    from tcp_tests.managers.jenkins import client
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
    env_host = os.environ.get('JENKINS_URL', None)
    env_username = os.environ.get('JENKINS_USER', None)
    env_password = os.environ.get('JENKINS_PASS', None)

    parser = argparse.ArgumentParser(description=(
        'Host, username and password may be specified either by the command '
        'line arguments or using environment variables: JENKINS_URL, '
        'JENKINS_USER, JENKINS_PASS.\nCommand line arguments have the highest '
        'priority, after that the environment variables are used as defaults.'
    ))
    parser.add_argument('--host',
                        metavar='JENKINS_URL',
                        help='Jenkins Host',
                        default=env_host)
    parser.add_argument('--username',
                        metavar='JENKINS_USER',
                        help='Jenkins Username',
                        default=env_username)
    parser.add_argument('--password',
                        metavar='JENKINS_PASS',
                        help='Jenkins Password or API token',
                        default=env_password)
    return parser


def get_nodes(host, username, password):
    """Get slave nodes list from Jenkins"""
    jenkins = client.JenkinsClient(host=host,
                                   username=username,
                                   password=password)
    nodes = jenkins.get_nodes()

    return nodes


def main(args=None):
    parser = load_params()
    opts = parser.parse_args()

    if opts.host is None:
        print("JENKINS_URL is required!")
        parser.print_help()
        return 10
    else:
        nodes = get_nodes(
            opts.host,
            opts.username,
            opts.password)
        for node in nodes:
            status = 'online' if node['offline'] is False else 'offline'
            print("{0}: {1}".format(node['name'], status))


if __name__ == "__main__":
    sys.exit(main())
