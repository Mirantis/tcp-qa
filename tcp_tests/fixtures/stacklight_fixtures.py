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
from tcp_tests.managers import sl_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def sl_actions(config, underlay_actions, salt_actions):
    """Fixture that provides various actions for K8S

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: SLManager

    For use in tests or fixtures to deploy a custom K8S
    """
    return sl_manager.SLManager(config, underlay_actions, salt_actions)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.stacklight_deployed)
@pytest.fixture(scope='function')
def stacklight_deployed(revert_snapshot, request, config,
                        hardware, underlay, salt_deployed,
                        sl_actions, core_deployed):
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
    # Deploy SL services
    if not config.stack_light.stacklight_installed:
        steps_path = config.sl_deploy.sl_steps_path
        commands = underlay.read_template(steps_path)
        sl_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.stacklight_deployed)
        salt_deployed.sync_time()

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return sl_actions


@pytest.mark.revert_snapshot(ext.SNAPSHOT.stacklight_deployed)
@pytest.fixture(scope='function')
def sl_os_deployed(revert_snapshot,
                   openstack_deployed,
                   stacklight_deployed):
    """Fixture to get or install SL and OpenStack services on environment

    Uses fixtures openstack_deployed and stacklight_deployed,
    with 'stacklight_deployed' top-level snapshot.

    Returns SLManager instance object
    """
    return stacklight_deployed
