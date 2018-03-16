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

import pytest

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests.managers import saltmanager

LOG = logger.logger


@pytest.fixture(scope='function')
def salt_actions(config, underlay):
    """Fixture that provides various actions for salt

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: SaltManager
    """
    return saltmanager.SaltManager(config, underlay)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.salt_deployed)
@pytest.fixture(scope='function')
def salt_deployed(revert_snapshot, request, config,
                  hardware, underlay, salt_actions, snapshot, grab_versions):
    """Fixture to get or install salt service on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param salt_actions: fixture provides SaltManager instance
    :rtype: SaltManager

    If config.salt.salt_master_host is not set, this fixture assumes that
    the salt was not installed, and do the following:
    - install salt master and salt minions
    - make snapshot with name 'salt_deployed'
    - return SaltManager

    If config.salt.salt_master_host was set, this fixture assumes that the
    salt was already deployed, and do the following:
    - return SaltManager instance

    If you want to revert 'salt_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("salt_deployed")
    """
    # Create Salt cluster
    if config.salt.salt_master_host == '0.0.0.0':
        # Temporary workaround. Underlay should be extended with roles
        config.salt.salt_master_host = \
            underlay.host_by_node_role(
                node_role=ext.UNDERLAY_NODE_ROLES.salt_master)

        commands = underlay.read_template(config.salt_deploy.salt_steps_path)
        LOG.info("############ Executing command ####### {0}".format(commands))
        salt_actions.install(commands)

        salt_nodes = salt_actions.get_ssh_data()
        config.underlay.ssh = config.underlay.ssh + \
            [node for node in salt_nodes
             if not any(node['node_name'] == n['node_name']
                        for n in config.underlay.ssh)]
        hardware.create_snapshot(ext.SNAPSHOT.salt_deployed)
        salt_actions.sync_time()

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    salt_actions.sync_time()

    return salt_actions
