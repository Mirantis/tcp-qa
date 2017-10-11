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

from tcp_tests.managers import opencontrail_manager


@pytest.fixture(scope='function')
def opencontrail(config, underlay, openstack_deployed):
    """Fixture that provides various actions for OpenContrail

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: OpenContrailManager

    """
#    if not config.opencontrail.opencontrail_prepare_tests_steps_path:
        

    return opencontrail_manager.OpenContrailManager(config, underlay,
                                                    openstack_deployed)
