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

from tcp_tests.managers import rallymanager


@pytest.fixture(scope='function')
def rally(request, config, underlay, salt_deployed):
    """Fixture that provides various actions for TCP

    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: RallyManager

    For use in tests or fixtures to deploy a custom TCP
    """
    with_rally = request.keywords.get('with_rally', None)
    rally_node = "gtw01."
    if with_rally:
        rally_node = with_rally.kwargs.get("rally_node", "gtw01.")

    return rallymanager.RallyManager(underlay, rally_node)
