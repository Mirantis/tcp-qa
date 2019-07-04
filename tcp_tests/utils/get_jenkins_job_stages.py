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
import time

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
    env_job_name = os.environ.get('JOB_NAME', 'deploy_openstack')
    env_build_number = os.environ.get('BUILD_NUMBER', 'lastBuild')

    parser = argparse.ArgumentParser(description=(
        'Host, username and password may be specified either by the command '
        'line arguments or using environment variables: JENKINS_URL, '
        'JENKINS_USER, JENKINS_PASS, JENKINS_START_TIMEOUT, '
        'JENKINS_BUILD_TIMEOUT. \nCommand line arguments have the highest '
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
    parser.add_argument('--job-name',
                        metavar='JOB_NAME',
                        help='Jenkins job name',
                        default=env_job_name)
    parser.add_argument('--build-number',
                        metavar='BUILD_NUMBER',
                        help='Jenkins job build number',
                        default=env_build_number)
    return parser


def get_deployment_result(host, username, password, job_name, build_number):
    """Get the pipeline job result from Jenkins

    Get all the stages resutls from the specified job,
    show error message if present.
    """
    jenkins = client.JenkinsClient(host=host,
                                   username=username,
                                   password=password,
                                   ssl_verify=False)

    def get_stages(nodes, indent=0, show_status=True):
        res = []
        for node in nodes:
            if show_status:
                msg = " " * indent + "{}: {}".format(node['name'],
                                                     node['status'])
                if 'error' in node and 'message' in node['error']:
                    msg += ", " + node['error']['message']
                res.append(msg)

            if node['status'] != 'SUCCESS':
                wf = jenkins.get_workflow(job_name, build_number,
                                          int(node['id']))
                if wf is not None:
                    if 'stageFlowNodes' in wf:
                        res += get_stages(wf['stageFlowNodes'], indent + 2,
                                          show_status=False)
                    elif '_links' in wf and 'log' in wf['_links']:
                        log = jenkins.get_workflow(job_name,
                                                   build_number,
                                                   int(node['id']),
                                                   mode='log')
                        if "text" in log:
                            prefix = " " * (indent + 2)
                            res.append("\n".join(
                                prefix + line
                                for line in log["text"].splitlines()))
        return res

    for _ in range(3):
        wf = jenkins.get_workflow(job_name, build_number)
        info = jenkins.build_info(job_name, int(wf['id']))
        if info.get('result'):
            break
        time.sleep(3)

    build_description = ("[" + info['fullDisplayName'] + "] " +
                         info['url'] + " : " + (info['result'] or 'No result'))
    stages = get_stages(wf['stages'], 0)
    if not stages:
        msg = wf['status'] + ":\n\n"
        stages = [msg + jenkins.get_build_output(job_name, int(wf['id']))]
    return (build_description, stages)


def main(args=None):
    parser = load_params()
    opts = parser.parse_args()

    if opts.host is None:
        print("JENKINS_URL is required!")
        parser.print_help()
        return 10
    else:
        (build_description, stages) = get_deployment_result(
            opts.host,
            opts.username,
            opts.password,
            opts.job_name,
            opts.build_number)
        print(build_description)
        print('\n'.join(stages))


if __name__ == "__main__":
    sys.exit(main())
