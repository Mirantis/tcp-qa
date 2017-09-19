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

LOG = logger.logger


class TestOSSInstaller(object):
    """Test class for testing Operational Support System Tools deployment"""

    @pytest.mark.fail_snapshot
    def test_oss_install_default(self, underlay, show_step,
                                 oss_deployed, openstack_deployed,
                                 sl_deployed):
        """Test for deploying an OSS environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup cid* nodes
            3. Setup OpenStack nodes
            4. Setup Stacklight

        """
        LOG.info("*************** DONE **************")
