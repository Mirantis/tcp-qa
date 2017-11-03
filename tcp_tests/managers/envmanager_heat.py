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

from retry import retry

from django.utils import functional

from heatclient import client as heatclient
# from novaclient import client as novaclient
from keystoneauth1.identity import V2Password
from keystoneauth1.session import Session as KeystoneSession
from oslo_config import cfg

from tcp_tests import settings
from tcp_tests import settings_oslo
from tcp_tests.helpers import ext
from tcp_tests.helpers import exceptions
from tcp_tests import logger

LOG = logger.logger


class EnvironmentManagerHeat(object):
    """Class-helper for creating VMs via devops environments"""

    __config = None
    __stack = None

    def __init__(self, config=None):
        """Create/connect to the Heat stack with test environment

        :param config: oslo.config object
        :param config.hardware.heat_version: Heat version
        :param config.hardware.heat_auth_url: OS auth URL to access heat
        :param config.hardware.heat_username: OS username
        :param config.hardware.heat_password: OS password
        :param config.hardware.heat_project_name: OS tenant name
        :param config.hardware.heat_stack_name: Name of the stack that should
                                                be created or connected to.
        """
        self.__config = config

        token = self._keystone_session.get_token()
        endpoint_url = self._keystone_session.get_endpoint(
            service_type='orchestration', endpoint_type='publicURL')
        self.__heatclient = heatclient.Client(
            version=config.hardware.heat_version, endpoint=endpoint_url,
            token=token)

    @property
    def __stack(self):
        return self._get_stack_by_name(
            name=self.__config.hardware.heat_stack_name)

#In [16]: stack = client.stacks.get('tleontovich_ovs01')
#In [28]: stack.outputs
#Out[28]:
#[{u'description': u'Public IP address of the Salt master node',
#  u'output_key': u'salt_master_ip',
#  u'output_value': u'185.22.97.227'}]


    @functional.cached_property
    def _keystone_session(self):
        keystone_auth = V2Password(
            auth_url=settings.OS_AUTH_URL or self.__config.hardware.heat_auth_url,
            username=settings.OS_USERNAME or self.__config.hardware.heat_username,
            password=settings.OS_PASSWORD or self.__config.hardware.heat_password,
            tenant_name=settings.OS_TENANT_NAME or self.__config.hardware.heat_project_name)
        return KeystoneSession(auth=keystone_auth, verify=False)



    def lvm_storages(self):
        """Returns a dict object of lvm storages in current environment

        returned data example:
            {
                "master": {
                    "id": "virtio-bff72959d1a54cb19d08"
                },
                "slave-0": {
                    "id": "virtio-5e33affc8fe44503839f"
                },
                "slave-1": {
                    "id": "virtio-10b6a262f1ec4341a1ba"
                },
            }

        :rtype: dict
        """
        result = {}
        for node in self.k8s_nodes:
            lvm = filter(lambda x: x.volume.name == 'lvm', node.disk_devices)
            if len(lvm) == 0:
                continue
            lvm = lvm[0]
            result[node.name] = {}
            result_node = result[node.name]
            result_node['id'] = "{bus}-{serial}".format(
                bus=lvm.bus,
                serial=lvm.volume.serial[:20])
            LOG.info("Got disk-id '{}' for node '{}'".format(
                result_node['id'], node.name))
        return result

    def _get_stack_by_name(self, name):
        """Get a heat stack by name

        :param name: string
        :rtype Stack: Heat 'Stack' object
        Raises 'HTTPNotFound' if stack not found
        """
        return self.__heatclient.stacks.get(name)

    def get_ssh_data(self, roles=None):
        """Generate ssh config for Underlay

        :param roles: list of strings
        """
#root@cfg01:~# salt-key -l acc
#Accepted Keys:
#cfg01.mk22-lab-ovs.local
#cmp01.mk22-lab-ovs.local
#cmp02.mk22-lab-ovs.local
#ctl01.mk22-lab-ovs.local
#ctl02.mk22-lab-ovs.local
#ctl03.mk22-lab-ovs.local
#gtw01.mk22-lab-ovs.local
#mon01.mk22-lab-ovs.local
#mon02.mk22-lab-ovs.local
#mon03.mk22-lab-ovs.local
#prx01.mk22-lab-ovs.local

#root@cfg01:~# salt '*' pillar.get _param:single_address
#prx01.mk22-lab-ovs.local:
#    172.16.10.121
#gtw01.mk22-lab-ovs.local:
#    172.16.10.110
#cmp01.mk22-lab-ovs.local:
#    172.16.10.105
#cmp02.mk22-lab-ovs.local:
#    172.16.10.106
#mon02.mk22-lab-ovs.local:
#mon01.mk22-lab-ovs.local:
#ctl01.mk22-lab-ovs.local:
#    172.16.10.101
#ctl03.mk22-lab-ovs.local:
#    172.16.10.103
#cfg01.mk22-lab-ovs.local:
#mon03.mk22-lab-ovs.local:
#ctl02.mk22-lab-ovs.local:
#    172.16.10.102

        if roles is None:
            raise Exception("No roles specified for the environment!")

        config_ssh = []
        for d_node in self._env.get_nodes(role__in=roles):
            ssh_data = {
                'node_name': d_node.name,
                'address_pool': self._get_network_pool(
                    ext.NETWORK_TYPE.public).address_pool.name,
                'host': self.node_ip(d_node),
                'login': settings.SSH_NODE_CREDENTIALS['login'],
                'password': settings.SSH_NODE_CREDENTIALS['password'],
            }
            config_ssh.append(ssh_data)
        return config_ssh

    def set_dns_config(self):
        # Set local nameserver to use by default
        if not self.__config.underlay.nameservers:
            self.__config.underlay.nameservers = [self.nameserver]
        if not self.__config.underlay.upstream_dns_servers:
            self.__config.underlay.upstream_dns_servers = [self.nameserver]

    def wait_node_is_offline(self, node_ip, timeout):
        """Wait node is shutdown and doesn't respond

        """
        helpers.wait(
            lambda: not helpers.tcp_ping(node_ip, 22),
            timeout=timeout,
            timeout_msg="Node '{}' didn't go offline after {} sec".format(
                node_ip, timeout
            )
        )

    def wait_node_is_online(self, node_ip, timeout):
        """Wait node is online after starting

        """
        helpers.wait(
            lambda: helpers.tcp_ping(node_ip, 22),
            timeout=timeout,
            timeout_msg="Node '{}' didn't become online after {} sec".format(
                node_ip, timeout
            )
        )

    def wait_of_stack_status(self, status, delay=5, tries=60):

        @retry(ValueError, delay=delay, tries=tries)
        def wait():
            st = self.__stack.stack_status
            if st == status:
                return
            else:
                LOG.info("Actial status is {}".format(st))
                raise ValueError
        LOG.info("Waiting {}".format(status))
        wait()

    def revert_snapshot(self, name):
        """Revert snapshot by name

        - Revert the heat snapshot in the environment
        - Try to reload 'config' object from a file 'config_<name>.ini'
          If the file not found, then pass with defaults.
        - Set <name> as the current state of the environment after reload

        :param name: string
        """
        LOG.info("Reverting from snapshot named '{0}'".format(name))

        if self.__stack is not None:
            snap = next((s for s in self.__stack.snapshot_list()['snapshots']
                         if s["name"] == name))
            uuid = snap['id']
            self.__stack.restore(uuid)
            self.wait_of_stack_status('RESTORE_COMPLETE')
        else:
            raise exceptions.EnvironmentIsNotSet()

        try:
            test_config_path = self._get_snapshot_config_name(name)
            settings_oslo.reload_snapshot_config(self.__config,
                                                 test_config_path)
        except cfg.ConfigFilesNotFoundError as conf_err:
            LOG.error("Config file(s) {0} not found!".format(
                conf_err.config_files))

        self.__config.hardware.current_snapshot = name

    def create_snapshot(self, name, description=None):
        """Create named snapshot of current env.

        - Create a snapshot for the environment
        - Save 'config' object to a file 'config_<name>.ini'

        :name: string
        """
        LOG.info("Creating snapshot named '{0}'".format(name))
        self.__config.hardware.current_snapshot = name
        LOG.info("current config '{0}'".format(
            self.__config.hardware.current_snapshot))
        if self.__stack is not None:
            LOG.info('trying to snapshot ....')
            self.__stack.snapshot(name, description=description, force=True)
        else:
            raise exceptions.EnvironmentIsNotSet()
        settings_oslo.save_config(self.__config, name, self._env.name)

    def _get_snapshot_config_name(self, snapshot_name):
        """Get config name for the environment"""
        env_name = self.__stack.stack_name
        if env_name is None:
            env_name = 'config'
        test_config_path = os.path.join(
            settings.LOGS_DIR, '{0}_{1}.ini'.format(env_name, snapshot_name))
        return test_config_path

    def has_snapshot(self, name):
        if name in (ext.SNAPSHOT.hardware, ext.SNAPSHOT.underlay):
            LOG.warning(
                "HEAT Manager doesn't support {} snapshot".format(name))
            return True
        return bool(next((s for s in self.__stack.snapshot_list()['snapshots']
                          if s["name"] == name), None))

    def has_snapshot_config(self, name):
        test_config_path = self._get_snapshot_config_name(name)
        return os.path.isfile(test_config_path)

    def start(self):
        """Start environment"""
        LOG.warning("HEAT Manager doesn't support start environment feature")
        pass

    def start(self):
        """Start environment"""
        LOG.warning("HEAT Manager doesn't support stop environment feature")
        pass
# TODO(ddmitriev): add all Environment methods
