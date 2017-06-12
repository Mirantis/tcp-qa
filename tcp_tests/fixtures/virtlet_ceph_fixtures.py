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

import pytest

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests.managers import virtlet_ceph_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def virtlet_ceph_actions(config, underlay):
    """Fixture that provides various actions for Virtlet project

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: VirtletCephManager
    """
    return virtlet_ceph_manager.VirtletCephManager(config, underlay)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.virtlet_ceph_deployed)
@pytest.fixture(scope='function')
def virtlet_ceph_deployed(revert_snapshot, config, hardware, underlay,
                          virtlet_deployed, virtlet_ceph_actions):
    """Fixture to get or install Virtlet project on the environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param virtlet_deployed: fixture provides VirtletManager instance
    :param virtlet_ceph_actions: fixture provides VirtletCephManager
    :rtype: VirtletCephManager

    If config.virtlet.ceph_installed is not set, this
    fixture assumes that the One-node Ceph for Virtlet was not installed,
    and do the following:
    - install One-node Ceph cluster to the desired node
    - make snapshot with name 'virtlet_ceph_deployed'
    - return VirtletCephManager

    If config.virtlet.ceph_installed was set, this fixture assumes that
    the One-node Ceph cluster was already installed, and do the following:
    - return VirtletCephManager instance

    If you want to revert 'virtlet_ceph_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("virtlet_ceph_deployed")
    """
    # Deploy Virtlet with Ceph for Kubernetes
    if not config.virtlet.ceph_installed:
        steps_path = config.virtlet_deploy.virtlet_ceph_steps_path
        commands = underlay.read_template(steps_path)
        virtlet_ceph_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.virtlet_ceph_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return virtlet_ceph_actions
