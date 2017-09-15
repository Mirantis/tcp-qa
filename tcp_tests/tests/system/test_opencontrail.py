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


@pytest.mark.deploy
class TestOpenContrail(object):
    """Test class for testing OpenContrail on a TCP lab"""

    @pytest.mark.fail_snapshot
    def test_opencontrail(self, config, openstack_deployed,
                          show_step, opencontrail):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Prepare contrail-tests on ctl01 node
            5. Run contrail-tests
        """
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        opencontrail.prepare_tests(
            config.opencontrail.opencontrail_prepare_tests_steps_path)

        opencontrail.run_tests(
            tags=config.opencontrail.opencontrail_tags,
            features=config.opencontrail.opencontrail_features)
