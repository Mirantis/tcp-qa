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
from tcp_tests.managers import openstack_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def openstack_actions(config, hardware, underlay, salt_deployed):
    """Fixture that provides various actions for OpenStack

    :param config: fixture provides oslo.config
    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :param salt_deployed: fixture provides salt manager
    :rtype: OpenstackManager

    For use in tests or fixtures to deploy a custom OpenStack
    """
    return openstack_manager.OpenstackManager(config, underlay,
                                              hardware, salt_deployed)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.openstack_deployed)
@pytest.fixture(scope='function')
def openstack_deployed(revert_snapshot, request, config,
                       hardware, underlay, common_services_deployed,
                       openstack_actions, rally):
    """Fixture to get or install OpenStack services on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param common_services_deployed: fixture provides CommonServicesManager
    :param openstack_actions: fixture provides OpenstackManager instance
    :param rally: fixture provides RallyManager instance
    :rtype: OpenstackManager

    If config.openstack.openstack_installed is not set, this fixture assumes
    that the openstack services were not installed, and do the following:
    - install openstack services
    - [optional] prepare docker with rally container
    - make snapshot with name 'openstack_deployed'
    - return OpenstackManager instance

    If config.openstack.openstack_installed was set, this fixture assumes that
    the openstack services were already installed, and do the following:
    - return OpenstackManager instance

    If you want to prepare 'rally', please use mark:
    @pytest.mark.with_rally(rally_node=<str>,
                            prepare_openstack=<bool>,
                            prepare_tempest=<bool>)
    :param rally_node: first chars of the node name where rally should
                       be started
    :param prepare_openstack: if True, prepare OpenStack objects for
                              rally tasks: cirros image, private net04

    If you want to revert 'openstack_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("openstack_deployed")
    """

    # Deploy Openstack cluster
    if not config.openstack.openstack_installed:
        steps_path = config.openstack_deploy.openstack_steps_path
        commands = underlay.read_template(steps_path)
        openstack_actions.install(commands)

        # If @pytest.mark.with_rally() is set, then prepare Rally
        # container for 'openstack_deployed' snapshot.
        with_rally = request.keywords.get('with_rally', None)
        if with_rally:
            prepare_openstack = with_rally.kwargs.get("prepare_openstack",
                                                      False)
            prepare_tempest = with_rally.kwargs.get("prepare_tempest", False)
            if prepare_openstack:
                rally.prepare_rally_task(target_node='ctl01')
            if prepare_tempest:
                rally.prepare_tempest_task()
            rally.run_container()

        hardware.create_snapshot(ext.SNAPSHOT.openstack_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.tcp.* options contain access credentials to the already
        #    installed TCP API endpoint
        pass

    return openstack_actions
