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


class TestFailover(object):
    """Test class for testing OpenStack nodes failover"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_warm_shutdown_ctl01_node(self, underlay, openstack_deployed,
                                      openstack_actions, show_step):
        """Test warm shutdown ctl01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Sync time before tempest run
            5. Run tempest smoke before failover
            6. Shutdown ctl01
            7. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        # STEP #5
        show_step(5)
        # TODO (tleontovich) Add assert to tempest results
        openstack_actions.run_tempest(pattern='smoke')
        # STEP #6
        show_step(6)
        openstack_actions.warm_shutdown_openstack_nodes('ctl01')
        # STEP #7
        show_step(7)
        openstack_actions.run_tempest(pattern='smoke')

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_restart_ctl01_node(self, underlay, openstack_deployed,
                                      openstack_actions, show_step):
        """Test restart ctl01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Sync time before tempest run
            5. Run tempest smoke before failover
            6. Restart ctl01
            7. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        # STEP #5
        show_step(5)
        # TODO (tleontovich) Add assert to tempest results
        openstack_actions.run_tempest(pattern='smoke')
        # STEP #6
        show_step(6)
        openstack_actions.warm_restart_nodes('ctl01')
        # STEP #7
        show_step(7)
        openstack_actions.run_tempest(pattern='smoke')

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_warm_shutdown_cmp01_node(self, underlay, openstack_deployed,
                                      openstack_actions, show_step):
        """Test warm shutdown cmp01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Sync time before tempest run
            5. Run tempest smoke before failover
            6. Shutdown cmp01
            7. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        # STEP #5
        show_step(5)
        # TODO (tleontovich) Add assert to tempest results
        openstack_actions.run_tempest(pattern='smoke')
        # STEP #6
        show_step(6)
        openstack_actions.warm_shutdown_openstack_nodes('cmp01')
        # STEP #7
        show_step(7)
        openstack_actions.run_tempest(pattern='smoke')

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_restart_cmp01_node(self, underlay, openstack_deployed,
                                openstack_actions, show_step):
        """Test restart cmp01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Sync time before tempest run
            5. Run tempest smoke before failover
            6. Restart cmp01
            7. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        # STEP #5
        show_step(5)
        # TODO (tleontovich) Add assert to tempest results
        openstack_actions.run_tempest(pattern='smoke')
        # STEP #6
        show_step(6)
        openstack_actions.warm_restart_nodes('cmp01')
        # STEP #7
        show_step(7)
        openstack_actions.run_tempest(pattern='smoke')

        LOG.info("*************** DONE **************")
