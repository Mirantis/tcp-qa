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


class TestOfflineDeployment(object):
    """docstring for TestOfflineDeployment"""

    @pytest.mark.grab_versions
    def test_boot_day1(self, hardware):
        group = hardware._get_default_node_group()
        LOG.info("Nodes - {}".format(group.get_nodes()))
