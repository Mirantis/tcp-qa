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
from tcp_tests.managers import ceph_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def ceph_actions(config, hardware, underlay, salt_deployed):
    """Fixture that provides various actions for OpenStack

    :param config: fixture provides oslo.config
    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :param salt_deployed: fixture provides salt manager
    :rtype: CephManager

    For use in tests or fixtures to deploy a custom OpenStack
    """
    return ceph_manager.CephManager(config, underlay, hardware, salt_deployed)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ceph_deployed)
@pytest.fixture(scope='function')
def ceph_deployed(revert_snapshot, request, config,
                  hardware, underlay, common_services_deployed,
                  ceph_actions):
    """Fixture to get or install Ceph services on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param common_services_deployed: fixture provides CommonServicesManager
    :param ceph_actions: fixture provides CephManager instance
    :rtype: CephManager

    If config.ceph.ceph_installed is not set, this fixture assumes
    that the ceph services were not installed, and do the following:
    - install ceph services
    - make snapshot with name 'ceph_deployed'
    - return CephManager instance

    If config.ceph.ceph_installed was set, this fixture assumes that
    the ceph services were already installed, and do the following:
    - return CephManager instance

    If you want to revert 'ceph_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("ceph_deployed")
    """
    # Deploy Ceph cluster
    if not config.ceph.ceph_installed:
        steps_path = config.ceph_deploy.ceph_steps_path
        commands = underlay.read_template(steps_path)
        ceph_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.ceph_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return ceph_actions
