#    Copyright 2018 Mirantis, Inc.
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
class TestInstallOvsPikeCeph(object):
    """Test class for test openstack with ceph and ovs deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_pike_ceph_all_ovs_install(self, underlay,
                                       openstack_deployed,
                                       ceph_deployed,
                                       openstack_actions,
                                       tempest_actions):
        """Test for deploying pike ovs with ceph and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Setup ceph RBD, replication factor 2 for cinder, nova, glance
        5. Run tempest

        """
        openstack_actions._salt.local(
                tgt='*', fun='cmd.run',
                args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")
