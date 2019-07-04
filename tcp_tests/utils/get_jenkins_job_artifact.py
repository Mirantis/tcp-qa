#!/usr/bin/env python
#    Copyright 2019 Mirantis, Inc.
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
    from tcp_tests.managers.jenkins.client import JenkinsClient
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
    env_job_name = os.environ.get('JOB_NAME', None)
    env_build_number = os.environ.get('BUILD_NUMBER', 'lastBuild')

    parser = argparse.ArgumentParser(description=(
        'Host, username and password may be specified either by the command '
        'line arguments or using environment variables: JENKINS_URL, '
        'JENKINS_USER, JENKINS_PASS. \nCommand line arguments have the highest'
        ' priority, after that the environment variables are used as defaults.'
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
    parser.add_argument('--job-name',
                        metavar='JOB_NAME',
                        help='Jenkins job name',
                        default=env_job_name)
    parser.add_argument('--build-number',
                        metavar='BUILD_NUMBER',
                        help='Jenkins job build number',
                        default=env_build_number)
    parser.add_argument('--artifact-path',
                        help='Relative path of the artifact in Jenkins',
                        default=None,
                        type=str)
    parser.add_argument('--destination-name',
                        help='Local filename for the saving artifact',
                        default=None,
                        type=str)
    return parser


def download_artifact(host, username, password,
                      job_name, build_number,
                      artifact_path, destination_name):

    jenkins = JenkinsClient(
        host=host,
        username=username,
        password=password,
        ssl_verify=False)

    content = jenkins.get_artifact(job_name, build_number,
                                   artifact_path, destination_name)

    with open(destination_name, 'wb') as f:
        f.write(content)


def main(args=None):
    parser = load_params()
    opts = parser.parse_args()

    if (opts.host is None or opts.job_name is None
            or opts.artifact_path is None or opts.destination_name is None):
        print("JENKINS_URL, job_name and destination_name are required!")
        parser.print_help()
        return 10
    else:
        download_artifact(
            opts.host,
            opts.username,
            opts.password,
            opts.job_name,
            opts.build_number,
            opts.artifact_path,
            opts.destination_name)


if __name__ == "__main__":
    sys.exit(main())
