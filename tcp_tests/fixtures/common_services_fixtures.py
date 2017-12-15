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
from tcp_tests.managers import common_services_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def common_services_actions(config, underlay, salt_actions):
    """Fixture that provides various actions for CommonServices

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: CommonServicesManager
    """
    return common_services_manager.CommonServicesManager(config, underlay,
                                                         salt_actions)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.common_services_deployed)
@pytest.fixture(scope='function')
def common_services_deployed(revert_snapshot, request, config,
                             hardware, underlay, salt_deployed,
                             common_services_actions):
    """Fixture to get or install common services on the environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param common_services_actions: fixture provides CommonServicesManager
                                    instance
    :rtype: CommonServicesManager

    If config.common_services.common_services_installed is not set, this
    fixture assumes that the common services were not installed
    , and do the following:
    - install common services
    - make snapshot with name 'common_services_deployed'
    - return CommonServicesManager

    If config.common_services.common_services_installed was set, this fixture
    assumes that the common services were already installed, and do
    the following:
    - return CommonServicesManager instance

    If you want to revert 'common_services_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("common_services_deployed")
    """
    # Create Salt cluster
    if not config.common_services.common_services_installed:
        steps_path = config.common_services_deploy.common_services_steps_path
        commands = underlay.read_template(steps_path)
        common_services_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.common_services_deployed)
        salt_deployed.sync_time()

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return common_services_actions
