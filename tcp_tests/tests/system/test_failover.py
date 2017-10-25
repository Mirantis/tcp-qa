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
            4. Shutdown ctl01
            5. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)
        # STEP #4
        show_step(4)
        openstack_actions.warm_shutdown_openstack_nodes('ctl01')
        # STEP #5
        show_step(5)
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
            4. Restart ctl01
            5. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions.warm_restart_nodes('ctl01')
        # STEP #5
        show_step(5)
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
            4. Shutdown cmp01
            5. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions.warm_shutdown_openstack_nodes('cmp01')
        # STEP #5
        show_step(5)
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
            4. Restart cmp01
            5. Run tempest smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions.warm_restart_nodes('cmp01')
        # STEP #5
        show_step(5)
        openstack_actions.run_tempest(pattern='smoke')

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_restart_mon01_node(self, underlay, openstack_deployed,
                                openstack_actions, sl_deployed,
                                show_step):
        """Test restart mon01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check targets before restart
            5. Restart mon01
            6. Check targets after restart
            6. Run LMA smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))
        sl_deployed.check_prometheus_targets(mon_nodes)
        before_result = sl_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        failed_tests = [test['name'] for test in
                        before_result if 'passed' not in test['outcome']]
        # STEP #5
        show_step(5)
        openstack_actions.warm_restart_nodes('mon01')
        # STEP #6
        show_step(6)
        sl_deployed.check_prometheus_targets(mon_nodes)
        # STEP #7
        show_step(7)
        # Run SL component tetsts
        after_result = sl_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        for test in after_result:
            if test['name'] not in failed_tests:
                assert 'passed' in test['outcome'], \
                    'Failed test {}'.format(test)
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_warm_shutdown_mon01_node(self, underlay, openstack_deployed,
                                      openstack_actions, sl_deployed,
                                      show_step):
        """Test warm shutdown mon01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Shutdown mon01
            5. Run LMA smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        openstack_actions.warm_shutdown_openstack_nodes('mon01')
        # STEP #5
        show_step(5)
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/test_smoke.py',
            'test_alerts.py')
        LOG.info("*************** DONE **************")
