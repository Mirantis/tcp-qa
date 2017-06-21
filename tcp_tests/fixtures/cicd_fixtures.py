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
from tcp_tests.managers import cicd_manager
from tcp_tests.helpers import utils

LOG = logger.logger


@pytest.fixture(scope='function')
def cicd_actions(config, underlay, salt_deployed):
    """Fixture that provides various actions for Cicd

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :param salt_deployed: fixture provides salt manager
    :rtype: CicdManager

    For use in tests or fixtures to deploy CI/CD
    """
    return cicd_manager.CicdManager(config, underlay, salt_deployed)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.cicd_deployed)
@pytest.fixture(scope='function')
def cicd_deployed(revert_snapshot, request, config,
                  hardware, underlay, common_services_deployed,
                  cicd_actions):
    """Fixture to get or install Cicd services on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param common_services_deployed: fixture provides CommonServicesManager
    :param cicd_actions: fixture provides CicdManager instance
    :rtype: CicdManager

    If config.cicd.cicd_installed is not set, this fixture assumes
    that the cicd services were not installed, and do the following:
    - install cicd services
    - make snapshot with name 'cicd_deployed'
    - return CicdManager instance

    If config.cicd.cicd_installed was set, this fixture assumes that
    the cicd services were already installed, and do the following:
    - return CicdManager instance

    If you want to revert 'cicd_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("cicd_deployed")
    """
    # Deploy CI/CD cluster
    if not config.cicd.cicd_installed:
        steps_path = config.cicd_deploy.cicd_steps_path
        commands = underlay.read_template(steps_path)
        cicd_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.cicd_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return cicd_actions

