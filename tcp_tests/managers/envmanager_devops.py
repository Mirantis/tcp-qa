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

from devops import error
from devops.helpers import helpers
from devops import models
from django import db
from oslo_config import cfg

from tcp_tests import settings
from tcp_tests import settings_oslo
from tcp_tests.helpers import env_config
from tcp_tests.helpers import ext
from tcp_tests.helpers import exceptions
from tcp_tests import logger

LOG = logger.logger


class EnvironmentManager(object):
    """Class-helper for creating VMs via devops environments"""

    __config = None

    def __init__(self, config=None):
        """Initializing class instance and create the environment

        :param config: oslo.config object
        :param config.hardware.conf_path: path to devops YAML template
        :param config.hardware.current_snapshot: name of the snapshot that
                                                 descriebe environment status.
        """
        self.__devops_config = env_config.EnvironmentConfig()
        self.__env = None
        self.__config = config

        if config.hardware.conf_path is not None:
            options = {
                'config': self.__config,
            }
            self._devops_config.load_template(config.hardware.conf_path,
                                              options=options)
        else:
            raise Exception("Devops YAML template is not set in config object")

        try:
            self._get_env_by_name(self._d_env_name)
            if not self.has_snapshot(config.hardware.current_snapshot):
                raise exceptions.EnvironmentSnapshotMissing(
                    self._d_env_name, config.hardware.current_snapshot)
        except error.DevopsObjNotFound:
            LOG.info("Environment doesn't exist, creating a new one")
            self._create_environment()
        self.set_dns_config()
        self.set_address_pools_config()

    @property
    def _devops_config(self):
        return self.__devops_config

    @_devops_config.setter
    def _devops_config(self, conf):
        """Setter for self.__devops_config

        :param conf: tcp_tests.helpers.env_config.EnvironmentConfig
        """
        if not isinstance(conf, env_config.EnvironmentConfig):
            msg = ("Unexpected type of devops config. Got '{0}' " +
                   "instead of '{1}'")
            raise TypeError(
                msg.format(
                    type(conf).__name__,
                    env_config.EnvironmentConfig.__name__
                )
            )
        self.__devops_config = conf

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
        for node in self.__env.get_nodes(role__in=ext.UNDERLAY_NODE_ROLES):
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

    @property
    def _d_env_name(self):
        """Get environment name from fuel devops config

        :rtype: string
        """
        return self._devops_config['env_name']

    def _get_env_by_name(self, name):
        """Set existing environment by name

        :param name: string
        """
        self.__env = models.Environment.get(name=name)

    def _get_default_node_group(self):
        return self.__env.get_group(name='default')

    def _get_network_pool(self, net_pool_name):
        default_node_group = self._get_default_node_group()
        network_pool = default_node_group.get_network_pool(name=net_pool_name)
        return network_pool

    def get_ssh_data(self, roles=None):
        """Generate ssh config for Underlay

        :param roles: list of strings
        """
        if roles is None:
            raise Exception("No roles specified for the environment!")

        config_ssh = []
        for d_node in self.__env.get_nodes(role__in=roles):
            ssh_data = {
                'node_name': d_node.name,
                'roles': [d_node.role],
                'address_pool': self._get_network_pool(
                    ext.NETWORK_TYPE.admin).address_pool.name,
                'host': self.node_ip(d_node),
                'login': settings.SSH_NODE_CREDENTIALS['login'],
                'password': settings.SSH_NODE_CREDENTIALS['password'],
                'keys': [k['private'] for k in self.__config.underlay.ssh_keys]
            }
            config_ssh.append(ssh_data)
        return config_ssh

    def create_snapshot(self, name, description=None, force=False):
        """Create named snapshot of current env.

        - Create a libvirt snapshots for all nodes in the environment
        - Save 'config' object to a file 'config_<name>.ini'

        :name: string
        """
        if not settings.MAKE_SNAPSHOT_STAGES and not force:
            msg = ("[ SKIP snapshot '{0}' because MAKE_SNAPSHOT_STAGES=false ]"
                   " {1}".format(name, description or ''))
            LOG.info("\n\n{0}\n{1}".format(msg, '*' * len(msg)))
            return
        msg = "[ Create snapshot '{0}' ] {1}".format(name, description or '')
        LOG.info("\n\n{0}\n{1}".format(msg, '*' * len(msg)))

        self.__config.hardware.current_snapshot = name
        LOG.info("Set current snapshot in config to '{0}'".format(
            self.__config.hardware.current_snapshot))
        if self.__env is not None:
            LOG.info('trying to suspend ....')
            self.__env.suspend()
            LOG.info('trying to snapshot ....')
            self.__env.snapshot(name, description=description, force=True)
            LOG.info('trying to resume ....')
            self.__env.resume()
        else:
            raise exceptions.EnvironmentIsNotSet()
        settings_oslo.save_config(self.__config, name, self.__env.name)

        if settings.VIRTUAL_ENV:
            venv_msg = "source {0}/bin/activate;\n".format(
                settings.VIRTUAL_ENV)
        else:
            venv_msg = ""
        LOG.info("To revert the snapshot:\n\n"
                 "************************************\n"
                 "{venv_msg}"
                 "dos.py revert {env_name} {snapshot_name};\n"
                 "dos.py resume {env_name};\n"
                 "# dos.py time-sync {env_name};  # Optional\n"
                 "ssh -i {key_file} {login}@{salt_master_host} "
                 "# Optional password: {password}\n"
                 "************************************\n"
                 .format(venv_msg=venv_msg,
                         env_name=self._d_env_name,
                         snapshot_name=name,
                         login=settings.SSH_NODE_CREDENTIALS['login'],
                         password=settings.SSH_NODE_CREDENTIALS['password'],
                         salt_master_host=self.__config.salt.salt_master_host,
                         key_file=self.__config.underlay.ssh_key_file))

    def _get_snapshot_config_name(self, snapshot_name):
        """Get config name for the environment"""
        env_name = self.__env.name
        if env_name is None:
            env_name = 'config'
        test_config_path = os.path.join(
            settings.LOGS_DIR, '{0}_{1}.ini'.format(env_name, snapshot_name))
        return test_config_path

    def revert_snapshot(self, name):
        """Revert snapshot by name

        - Revert a libvirt snapshots for all nodes in the environment
        - Try to reload 'config' object from a file 'config_<name>.ini'
          If the file not found, then pass with defaults.
        - Set <name> as the current state of the environment after reload

        :param name: string
        """
        if not settings.MAKE_SNAPSHOT_STAGES:
            LOG.info("SKIP reverting from snapshot '{0}' "
                     "because MAKE_SNAPSHOT_STAGES=false".format(name))
            return

        if self.__env is not None:
            LOG.info("Suspending environment to stop IO")
            self.__env.suspend()
            LOG.info("Reverting from snapshot named '{0}'".format(name))
            self.__env.revert(name=name)
            LOG.info("Resuming environment after revert")
            self.__env.resume()
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

    def _create_environment(self):
        """Create environment and start VMs.

        If config was provided earlier, we simply create and start VMs,
        otherwise we tries to generate config from self.config_file,
        """
        if self._devops_config.config is None:
            raise exceptions.DevopsConfigPathIsNotSet()
        settings = self._devops_config
        env_name = settings['env_name']
        LOG.debug(
            'Preparing to create environment named "{0}"'.format(env_name)
        )
        if env_name is None:
            LOG.error('Environment name is not set!')
            raise exceptions.EnvironmentNameIsNotSet()
        try:
            self.__env = models.Environment.create_environment(
                settings.config
            )
        except db.IntegrityError:
            LOG.error(
                'Seems like environment {0} already exists or contain errors'
                ' in template.'.format(env_name)
            )
            raise
        self.__env.define()
        LOG.info(
            'Environment "{0}" created'.format(env_name)
        )

    def start(self, underlay_node_roles, timeout=480):
        """Method for start environment

        """
        if self.__env is None:
            raise exceptions.EnvironmentIsNotSet()
        self.__env.start()
        LOG.info('Environment "{0}" started'.format(self.__env.name))
        for node in self.__env.get_nodes(role__in=underlay_node_roles):
            LOG.info("Waiting for SSH on node '{0}' / {1} ...".format(
                node.name, self.node_ip(node)))
            helpers.wait_ssh_cmd(
                self.node_ip(node), 22, 'test -f /is_cloud_init_finish', timeout=timeout)
            # helpers.wait(
            #     lambda: helpers.tcp_ping(self.node_ip(node), 22),
            #     timeout=timeout,
            #     timeout_msg="Node '{}' didn't open SSH in {} sec".format(
            #         node.name, timeout
            #     )
            # )
        LOG.info('Environment "{0}" ready'.format(self.__env.name))

    def resume(self):
        """Resume environment"""
        if self.__env is None:
            raise exceptions.EnvironmentIsNotSet()
        self.__env.resume()

    def suspend(self):
        """Suspend environment"""
        if self.__env is None:
            raise exceptions.EnvironmentIsNotSet()
        self.__env.suspend()

    def stop(self):
        """Stop environment"""
        if self.__env is None:
            raise exceptions.EnvironmentIsNotSet()
        self.__env.destroy()

    def destroy_node(self, node_name):
        """Destroy node"""
        node = self.__env.get_node(name=node_name)
        node.destroy()

    def start_node(self, node_name):
        """Start node"""
        node = self.__env.get_node(name=node_name)
        node.start()

    def reboot_node(self, node_name):
        """Reboot node"""
        node = self.__env.get_node(name=node_name)
        node.reboot()

    def remove_node(self, node_name):
        """Remove node"""
        node = self.__env.get_node(name=node_name)
        node.remove()

    def wait_for_node_state(self, node_name, state, timeout):
        node = self.__env.get_node(name=node_name)
        if 'active' in state:
            helpers.wait(lambda: node.is_active(),
                         timeout=timeout,
                         timeout_msg=('Node {0} failed '
                                      'to become active'.format(node)))
        else:
            helpers.wait(lambda: not node.is_active(),
                         timeout=timeout,
                         timeout_msg=('Node {0} failed '
                                      'to become active'.format(node)))

    def has_snapshot(self, name):
        return self.__env.has_snapshot(name)

    def has_snapshot_config(self, name):
        test_config_path = self._get_snapshot_config_name(name)
        return os.path.isfile(test_config_path)

    def delete_environment(self):
        """Delete environment

        """
        LOG.debug("Deleting environment")
        self.__env.erase()

    def __get_nodes_by_role(self, node_role):
        """Get node by given role name

        :param node_role: string
        :rtype: devops.models.Node
        """
        LOG.debug('Trying to get nodes by role {0}'.format(node_role))
        return self.__env.get_nodes(role=node_role)

    def __get_nodes_by_name(self, node_name):
        """Get node by given role name

        :param node_name: string
        :rtype: devops.models.Node
        """
        LOG.debug('Trying to get nodes by role {0}'.format(node_name))
        return self.__env.get_nodes(name=node_name)

    @property
    def master_nodes(self):
        """Get all master nodes

        :rtype: list
        """
        nodes = self.__get_nodes_by_role(
            node_role=ext.UNDERLAY_NODE_ROLES.salt_master)
        return nodes

    @property
    def slave_nodes(self):
        """Get all slave nodes

        :rtype: list
        """
        nodes = self.__get_nodes_by_role(
            node_role=ext.UNDERLAY_NODE_ROLES.salt_minion)
        return nodes

    @staticmethod
    def node_ip(node):
        """Determine node's IP

        :param node: devops.models.Node
        :return: string
        """
        LOG.debug('Trying to determine {0} ip.'.format(node.name))
        return node.get_ip_address_by_network_name(
            ext.NETWORK_TYPE.admin
        )

    @property
    def nameserver(self):
        return self.__env.router(ext.NETWORK_TYPE.admin)

    def set_dns_config(self):
        # Set local nameserver to use by default
        if not self.__config.underlay.nameservers:
            self.__config.underlay.nameservers = [self.nameserver]
        if not self.__config.underlay.upstream_dns_servers:
            self.__config.underlay.upstream_dns_servers = [self.nameserver]

    def set_address_pools_config(self):
        """Store address pools CIDRs in config object"""
        for ap in self.__env.get_address_pools():
            self.__config.underlay.address_pools[ap.name] = ap.net
