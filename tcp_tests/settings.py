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
import pkg_resources
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

LAB_CONFIG_NAME = os.environ.get('LAB_CONFIG_NAME', 'mk22-lab-basic')
#LAB_CONFIGS_NAME = os.environ.get('LAB_NAME', 'mk22-lab-advanced')

SSH_LOGIN = os.environ.get('SSH_LOGIN', 'root')
SSH_PASSWORD = os.environ.get('SSH_PASSWORD', 'r00tme')
SSH_NODE_CREDENTIALS = {"login": SSH_LOGIN,
                        "password": SSH_PASSWORD}

SHUTDOWN_ENV_ON_TEARDOWN = get_var_as_bool('SHUTDOWN_ENV_ON_TEARDOWN', True)

# public_iface = IFACES[0]
# private_iface = IFACES[1]
IFACES = [
    os.environ.get("IFACE_0", "eth0"),
    os.environ.get("IFACE_1", "eth1"),
]

SALT_USER = os.environ.get('SALT_USER', 'salt')
SALT_PASSWORD = os.environ.get('SALT_PASSWORD', 'hovno12345!')

DOCKER_REGISTRY = os.environ.get('DOCKER_REGISTRY',
                                 'docker-prod-virtual.docker.mirantis.net')
HYPERKUBE_IMAGE = os.environ.get(
    'HYPERKUBE_IMAGE', 'mirantis/kubernetes/hyperkube-amd64:v1.6.2-2')
CALICO_IMAGE = os.environ.get('CALICO_IMAGE',
                              'mirantis/projectcalico/calico/node:latest')
CALICOCTL_IMAGE = os.environ.get('CALICOCTL_IAMGE',
                                 'mirantis/projectcalico/calico/ctl:latest')
CALICO_CNI_IMAGE = os.environ.get('CALICO_CNI_IMAGE',
                                  'mirantis/projectcalico/calico/cni:latest')
NETCHECKER_AGENT = os.environ.get('NETCHECKER_AGENT',
                                  'mirantis/k8s-netchecker-agent:latest')
NETCHECKER_SERVER = os.environ.get('NETCHECKER_SERVER',
                                   'mirantis/k8s-netchecker-server:latest')
DOCKER_PACKAGE = os.environ.get('DOCKER_PACKAGE', '')
