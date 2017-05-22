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
import yaml

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests import settings
from tcp_tests.managers import sl_manager
from tcp_tests.helpers import utils

LOG = logger.logger


@pytest.fixture(scope='function')
def sl_actions(config, underlay, salt_deployed):
    """Fixture that provides various actions for K8S

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: SLManager

    For use in tests or fixtures to deploy a custom K8S
    """
    return sl_manager.SLManager(config, underlay, salt_deployed)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.sl_deployed)
@pytest.fixture(scope='function')
def sl_deployed(revert_snapshot, request, config,
                       hardware, underlay, common_services_deployed,
                       sl_actions):
    """Fixture to get or install SL services on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param tcp_actions: fixture provides SLManager instance
    :rtype: SLManager
    """
    # Create Salt cluster
    if not config.stack_light.sl_installed:
        steps_path = config.sl_deploy.sl_steps_path
        commands = underlay.read_template(steps_path)
        sl_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.sl_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return sl_actions


@pytest.mark.revert_snapshot(ext.SNAPSHOT.sl_deployed)
@pytest.fixture(scope='function')
def deploy_sl(revert_snapshot, request, config,
              hardware, underlay, common_services_deployed,
              sl_actions):
    """Fixture to get or install OpenStack services on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param tcp_actions: fixture provides OpenstackManager instance
    :rtype: SLManager

    If you want to revert 'sl_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("sl_deployed")
    """
    # Create Salt cluster
    if not config.stack_light.sl_installed:
        steps_path = config.sl_deploy.sl_steps_path
        commands = utils.read_template(steps_path)
        sl_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.sl_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return sl_actions
