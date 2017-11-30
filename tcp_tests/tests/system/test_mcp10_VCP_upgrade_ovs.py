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

LOG = logger.logger


@pytest.mark.deploy
class TestMCP10OvsVCPUpgrade(object):
    """Test class for testing mcp10 vxlan deploy"""

    @pytest.mark.fail_snapshot
    def test_mcp10_VCP_upgrade_ovs(self, underlay, openstack_deployed,
                                     show_step):
        """Test for deploying an mcp environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")
