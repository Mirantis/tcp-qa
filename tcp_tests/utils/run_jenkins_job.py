#!/usr/bin/env python

import argparse
import os
import sys

import json

sys.path.append(os.getcwd())
try:
    from tcp_tests.managers.jenkins.client import JenkinsClient
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)


EXIT_CODES = {
  "SUCCESS": 0,
  # 1 - python runtime execution error
  # 2 - job unknown status
  "FAILURE": 3,
  "UNSTABLE": 4,
  "ABORTED": 5,
  "DISABLED": 6
  # 10 - invalid cli options
}


def load_params():
    """
    Parse CLI arguments and environment variables

    Returns: ArgumentParser instance
    """
    env_host = os.environ.get('JENKINS_URL', None)
    env_username = os.environ.get('JENKINS_USER', None)
    env_password = os.environ.get('JENKINS_PASS', None)
    env_start_timeout = os.environ.get('JENKINS_START_TIMEOUT', 1800)
    env_build_timeout = os.environ.get('JENKINS_BUILD_TIMEOUT', 3600 * 4)

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
                        help='Jenkins Username', default=env_username)
    parser.add_argument('--password',
                        metavar='JENKINS_PASS',
                        help='Jenkins Password or API token',
                        default=env_password)
    parser.add_argument('--start-timeout',
                        metavar='JENKINS_START_TIMEOUT',
                        help='Timeout waiting until build is started',
                        default=env_start_timeout,
                        type=int)
    parser.add_argument('--build-timeout',
                        metavar='JENKINS_BUILD_TIMEOUT',
                        help='Timeout waiting until build is finished',
                        default=env_build_timeout,
                        type=int)
    parser.add_argument('--job-name',
                        help='Jenkins job name to run',
                        default=None)
    parser.add_argument('--job-parameters',
                        metavar='json-dict',
                        help=('Job parameters to use instead of default '
                              'values, as a json string, for example: '
                              '--job-parameters=\'{"SALT_MASTER_URL": '
                              '"http://localhost:6969"}\''),
                        default={}, type=json.loads)
    parser.add_argument('--job-output-prefix',
                        help=('Jenkins job output prefix for each line in the '
                              'output, if --verbose is enabled. Useful for the'
                              ' pipelines that use multiple different runs of '
                              'jobs. The string is a template for python '
                              'format() function where the following arguments'
                              ' are allowed: job_name, build_number. '
                              'Example: --job-output-prefix=\"[ {job_name} '
                              '#{build_number}, core ]\"'),
                        default='',
                        type=str)
    parser.add_argument('--verbose',
                        action='store_const',
                        const=True,
                        help='Show build console output',
                        default=False)
    return parser


def print_build_header(build, job_params, build_timeout):
    print('\n#############################################################')
    print('##### Building job [{0}] #{1} (timeout={2}) with the following '
          'parameters:'.format(build[0], build[1], build_timeout))
    print('##### ' + '\n##### '.join(
        [str(key) + ": " + str(val) for key, val in job_params.iteritems()]
    ))
    print('#############################################################')


def print_build_footer(build, result, url):
    print('\n\n#############################################################')
    print('##### Completed job [{0}] #{1} at {2}: {3}'
          .format(build[0], build[1], url, result))
    print('#############################################################\n')


def run_job(host, username, password,
            job_name, job_parameters=None, job_output_prefix='',
            start_timeout=1800, build_timeout=3600 * 4, verbose=False):

    jenkins = JenkinsClient(
        host=host,
        username=username,
        password=password,
        ssl_verify=False)

    job_params = jenkins.make_defults_params(job_name)
    if job_parameters is not None:  # job_parameters = {}
        job_params.update(job_parameters)

    build = jenkins.run_build(job_name,
                              job_params,
                              verbose=verbose,
                              timeout=start_timeout)
    if verbose:
        print_build_header(build, job_params, build_timeout)

    try:
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=build_timeout,
            interval=1,
            verbose=verbose,
            job_output_prefix=job_output_prefix)
    except Exception as e:
        print(str(e))
        raise

    result = jenkins.build_info(name=build[0],
                                build_id=build[1])['result']
    if verbose:
        print_build_footer(build, result, host)

    return result


def main(args=None):
    parser = load_params()
    opts = parser.parse_args()

    if opts.host is None or opts.job_name is None:
        print("JENKINS_URL and a job name are required!")
        parser.print_help()
        return 10
    else:
        result = run_job(
            opts.host,
            opts.username,
            opts.password,
            opts.job_name,
            opts.job_parameters,
            opts.job_output_prefix,
            opts.start_timeout,
            opts.build_timeout,
            opts.verbose)
        return EXIT_CODES.get(result, 2)


if __name__ == "__main__":
    sys.exit(main())
