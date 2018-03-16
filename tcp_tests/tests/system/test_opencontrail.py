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
from tcp_tests import settings

LOG = logger.logger


@pytest.mark.deploy
class TestOpenContrail(object):
    """Test class for testing OpenContrail on a TCP lab"""

    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="ctl01.")
    def test_opencontrail(self, config, openstack_deployed,
                          show_step, sl_deployed):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Prepare contrail-tests on ctl01 node
            5. Run contrail-tests
        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_deployed.run_tempest(target='ctl01',
                                           pattern=settings.PATTERN)
            openstack_deployed.download_tempest_report(stored_node='ctl01')
        LOG.info("*************** DONE **************")

        # opencontrail.prepare_tests(
        #     config.opencontrail.opencontrail_prepare_tests_steps_path)

        # opencontrail.run_tests(
        #     tags=config.opencontrail.opencontrail_tags,
        #     features=config.opencontrail.opencontrail_features)
