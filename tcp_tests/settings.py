#    Copyright 2016 Mirantis, Inc.
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
import os
import time

_boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}


def get_var_as_bool(name, default):
    value = os.environ.get(name, '')
    return _boolean_states.get(value.lower(), default)


LOGS_DIR = os.environ.get('LOGS_DIR', os.getcwd())
TIMESTAT_PATH_YAML = os.environ.get(
    'TIMESTAT_PATH_YAML', os.path.join(
        LOGS_DIR, 'timestat_{}.yaml'.format(time.strftime("%Y%m%d"))))

VIRTUAL_ENV = os.environ.get("VIRTUAL_ENV", None)
ENV_NAME = os.environ.get("ENV_NAME", None)
MAKE_SNAPSHOT_STAGES = get_var_as_bool("MAKE_SNAPSHOT_STAGES", True)
SHUTDOWN_ENV_ON_TEARDOWN = get_var_as_bool('SHUTDOWN_ENV_ON_TEARDOWN', True)

LAB_CONFIG_NAME = os.environ.get('LAB_CONFIG_NAME', 'mk22-lab-basic')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME',
                             '{}.local'.format(LAB_CONFIG_NAME))
# LAB_CONFIGS_NAME = os.environ.get('LAB_NAME', 'mk22-lab-advanced')

SSH_LOGIN = os.environ.get('SSH_LOGIN', 'root')
SSH_PASSWORD = os.environ.get('SSH_PASSWORD', 'r00tme')
SSH_NODE_CREDENTIALS = {"login": SSH_LOGIN,
                        "password": SSH_PASSWORD}

# http://docs.paramiko.org/en/2.4/api/transport.html\
# #paramiko.transport.Transport.set_keepalive
# If this is set, after interval seconds without sending any data over the
# connection, a "keepalive" packet will be sent (and ignored by the remote
# host). Similar to ServerAliveInterval for ssh_config.
# '0' to disable keepalives.
SSH_SERVER_ALIVE_INTERVAL = int(
    os.environ.get('SSH_SERVER_ALIVE_INTERVAL', 60))

# public_iface = IFACES[0]
# private_iface = IFACES[1]
IFACES = [
    os.environ.get("IFACE_0", "eth0"),
    os.environ.get("IFACE_1", "eth1"),
]

SALT_USER = os.environ.get('SALT_USER', 'salt')
SALT_PASSWORD = os.environ.get('SALT_PASSWORD', 'hovno12345!')

DOCKER_REGISTRY = os.environ.get('DOCKER_REGISTRY',
                                 'docker-prod-local.artifactory.mirantis.com')
BINARY_REGISTRY = os.environ.get('BINARY_REGISTRY', 'https://'
                                 'docker-prod-local.artifactory.mirantis.com/'
                                 'artifactory/binary-prod-local')
DOCKER_NAME = os.environ.get('DOCKER_NAME',
                             'mirantis/oscore/rally-tempest:latest')
DOCKER_IMAGES_SL_TAG = os.environ.get('DOCKER_IMAGES_SL_TAG', 'latest')

PATTERN = os.environ.get('PATTERN', None)
RUN_TEMPEST = get_var_as_bool('RUN_TEMPEST', False)
RUN_SL_TESTS = get_var_as_bool('RUN_SL_TESTS', False)

TEMPEST_IMAGE = os.environ.get(
    'TEMPEST_IMAGE',
    'docker-prod-virtual.docker.mirantis.net/mirantis/cicd/ci-tempest')  # noqa
TEMPEST_IMAGE_VERSION = os.environ.get('TEMPEST_IMAGE_VERSION', 'pike')
TEMPEST_PATTERN = os.environ.get('TEMPEST_PATTERN', 'tempest')
TEMPEST_TIMEOUT = int(os.environ.get('TEMPEST_TIMEOUT', 60 * 60 * 6))
TEMPEST_THREADS = int(os.environ.get('TEMPEST_THREADS', 2))
TEMPEST_EXTRA_ARGS = os.environ.get('TEMPEST_EXTRA_ARGS', '')
TEMPEST_TARGET = os.environ.get('TEMPEST_TARGET', 'gtw01')
SALT_VERSION = os.environ.get('SALT_VERSION', '2017.7')

# REPOSITORY_SUITE is always defined in swarm-run-pytest from MCP_VERSION
REPOSITORY_SUITE = os.environ.get('REPOSITORY_SUITE', 'proposed')
MCP_VERSION = os.environ.get('MCP_VERSION', REPOSITORY_SUITE)

SL_TEST_REPO = os.environ.get('SL_TEST_REPO',
                              'https://github.com/Mirantis/stacklight-pytest')
SL_TEST_COMMIT = os.environ.get('SL_TEST_COMMIT', 'master')

EXTERNAL_ADDRESS_POOL_NAME = os.environ.get('EXTERNAL_ADDRESS_POOL_NAME',
                                            'external-pool01')

STACK_INSTALL = os.environ.get('STACK_INSTALL', None)
SKIP_SYNC_TIME = get_var_as_bool("SKIP_SYNC_TIME", False)

# OpenStack parameters to work with Heat stacks
OS_HEAT_VERSION = os.environ.get('OS_HEAT_VERSION', 1)
OS_AUTH_URL = os.environ.get('OS_AUTH_URL', None)
OS_USERNAME = os.environ.get('OS_USERNAME', None)
OS_PASSWORD = os.environ.get('OS_PASSWORD', None)
OS_PROJECT_NAME = os.environ.get('OS_PROJECT_NAME', None)
LAB_PARAM_DEFAULTS = os.environ.get('LAB_PARAM_DEFAULTS', '')
