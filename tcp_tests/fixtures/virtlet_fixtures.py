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

import os

import pytest
import yaml

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests import settings
from tcp_tests.managers import virtlet_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def virtlet_actions(config, underlay, salt_actions):
    """Fixture that provides various actions for Virtlet project

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: VirtletManager
    """
    return virtlet_manager.VirtletManager(config, underlay, salt_actions)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.virtlet_deployed)
@pytest.fixture(scope='function')
def virtlet_deployed(revert_snapshot, request, config,
                             hardware, underlay, common_services_deployed,
                             virtlet_actions):
    """Fixture to get or install Virtlet project on the environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param virtlet_actions: fixture provides VirtletManager instance
    :rtype: VirtletManager

    If config.virtlet.virtlet_installed is not set, this
    fixture assumes that the Virtlet project was not installed,
    and do the following:
    - install Virtlet project
    - make snapshot with name 'virtlet_deployed'
    - return VirtletManager

    If config.virtlet.virtlet_installed was set, this fixture assumes that
    the Virtlet project was already installed, and do the following:
    - return VirtletManager instance

    If you want to revert 'virtlet_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("virtlet_deployed")
    """
    # Create Salt cluster
    if not config.virtlet.virtlet_installed:
        steps_path = config.virtlet_deploy.virtlet_steps_path
        commands = underlay.read_template(steps_path)
        virtlet_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.virtlet_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return virtlet_actions
