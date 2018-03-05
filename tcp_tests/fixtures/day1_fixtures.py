#    Copyright 2018 Mirantis, Inc.
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

from collections import namedtuple
import pytest

from tcp_tests.helpers import ext
from tcp_tests import logger
from tcp_tests.managers import saltmanager
from tcp_tests.managers import underlay_ssh_manager

LOG = logger.logger


@pytest.mark.revert_snapshot(ext.SNAPSHOT.day1_underlay)
@pytest.fixture(scope="function")
def day1_underlay(revert_snapshot, config, hardware):
    """Fixture that should provide SSH access to underlay objects.

    - Starts the 'hardware' environment and creates 'underlay' with required
      configuration.
    - Fills the following object using the 'hardware' fixture:
      config.underlay.ssh = JSONList of SSH access credentials for nodes.
                            This list will be used for initialization the
                            model UnderlaySSHManager, see it for details.

    :rtype UnderlaySSHManager: Object that encapsulate SSH credentials;
                               - provide list of underlay nodes;
                               - provide SSH access to underlay nodes using
                                 node names or node IPs.
    """
    # Create Underlay
    if not config.day1_underlay.ssh:
        # If config.underlay.ssh wasn't provided from external config, then
        # try to get necessary data from hardware manager (fuel-devops)

        # for devops manager: power on nodes and wait for SSH
        # for empty manager: do nothing
        # for maas manager: provision nodes and wait for SSH
        # hardware.start(underlay_node_roles=config.underlay.roles,
        hardware.start(
            underlay_node_roles=['salt_master'],
            timeout=config.underlay.bootstrap_timeout)

        config.day1_underlay.ssh = hardware.get_ssh_data(
            roles=config.underlay.roles)

        underlay = underlay_ssh_manager.UnderlaySSHManager(config)

        LOG.info("Generate MACs for MaaS")
        macs = {
            n.name.split('.')[0]: {
                "interface": {
                    "mac": n.get_interface_by_network_name('admin').mac_address}}  # noqa
            for n in hardware.slave_nodes}

        config.day1_cfg_config.maas_machines_macs = {
            "parameters": {
                "maas": {
                    "region": {
                        "machines": macs}}}}

        if not config.day1_underlay.lvm:
            underlay.enable_lvm(hardware.lvm_storages())
            config.day1_underlay.lvm = underlay.config_lvm

        hardware.create_snapshot(ext.SNAPSHOT.day1_underlay)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        underlay = underlay_ssh_manager.UnderlaySSHManager(config)

    return underlay


@pytest.mark.revert_snapshot(ext.SNAPSHOT.cfg_configured)
@pytest.fixture(scope='function')
def day1_cfg_config(revert_snapshot, request, config, hardware, underlay,
                    salt_actions, snapshot, grab_versions):
    """Fixture to get or install cfg node from day1 image on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param day1_underlay: fixture provides underlay manager
    :param salt_actions: fixture provides SaltManager instance
    :rtype: SaltManager

    If config.salt.salt_master_host is not set, this fixture assumes that
    the salt was not installed, and do the following:
    - install salt master and salt minions
    - make snapshot with name 'cfg_configured'
    - return SaltManager

    If config.salt.salt_master_host was set, this fixture assumes that the
    salt was already deployed, and do the following:
    - return SaltManager instance

    If you want to revert 'cfg_configured' snapshot, please use mark:
    @pytest.mark.revert_snapshot("cfg_configured")
    """
    # Create Salt cluster
    if config.salt.salt_master_host == '0.0.0.0':
        # Temporary workaround. Underlay should be extended with roles
        config.salt.salt_master_host = \
            underlay.host_by_node_role(
                node_role=ext.UNDERLAY_NODE_ROLES.salt_master)

        commands = underlay.read_template(
            config.day1_cfg_config.configure_steps_path)
        LOG.info("############ Executing command ####### {0}".format(commands))
        salt_actions.install(commands)

        salt_nodes = salt_actions.get_ssh_data()
        config.underlay.ssh = config.underlay.ssh + \
            [node for node in salt_nodes
             if not any(node['node_name'] == n['node_name']
                        for n in config.underlay.ssh)]

        hardware.create_snapshot(ext.SNAPSHOT.cfg_configured)
        salt_actions.sync_time()

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    salt_actions.sync_time()

    Collection = namedtuple(
        'Collection', ['salt', 'underlay', 'config'], verbose=True)

    return Collection(salt_actions, underlay, config)


@pytest.fixture(scope='function')
def day1_salt_actions(config, day1_underlay):
    """Fixture that provides various actions for salt

    :param config: fixture provides oslo.config
    :param day1_underlay: fixture provides underlay manager
    :rtype: SaltManager
    """
    return saltmanager.SaltManager(config, day1_underlay)
