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
import pytest

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests import settings
from tcp_tests.managers import tcpmanager

LOG = logger.logger


@pytest.fixture(scope='function')
def tcp_actions(config, underlay):
    """Fixture that provides various actions for K8S

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: K8SManager

    For use in tests or fixtures to deploy a custom K8S
    """
    return tcpmanager.TCPManager(config, underlay)


@pytest.fixture(scope='function')
def tcpcluster(revert_snapshot, request, config,
               hardware, underlay, tcp_actions):
    """Fixture to get or install TCP on environment

    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param tcp_actions: fixture provides TCPManager instance
    :rtype: TCPManager

    If config.tcp.tcp_host is not set, this fixture assumes that
    the tcp cluster was not deployed, and do the following:
    - deploy tcp cluster
    - make snapshot with name 'tcp_deployed'
    - return TCPCluster instance

    If config.tcp.tcp_host was set, this fixture assumes that the tcp
    cluster was already deployed, and do the following:
    - return TCPCluster instance

    If you want to revert 'tcp_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("tcp_deployed")
    """
    # If no snapshot was reverted, then try to revert the snapshot
    # that belongs to the fixture.
    # Note: keep fixtures in strict dependences from each other!
    if not revert_snapshot:
        if hardware.has_snapshot(ext.SNAPSHOT.tcp_deployed) and \
                hardware.has_snapshot_config(ext.SNAPSHOT.tcp_deployed):
            hardware.revert_snapshot(ext.SNAPSHOT.tcp_deployed)

    # Create TCP cluster
    if config.tcp.tcp_host == '0.0.0.0':

        tcp_actions.install_tcp()
        hardware.create_snapshot(ext.SNAPSHOT.tcp_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return tcp_actions
