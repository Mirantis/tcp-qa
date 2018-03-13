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
from tcp_tests.helpers import ext

LOG = logger.logger


class TestFailoverNodes(object):
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
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.sl_deployed)
    def test_restart_mon01_node(self, openstack_actions,
                                sl_os_deployed, show_step):
        """Test restart mon01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check targets before restart
            5. Restart mon01
            6. Check targets after restart
            7. Run LMA smoke after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        mon_nodes = sl_os_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))
        sl_os_deployed.check_prometheus_targets(mon_nodes)
        before_result = sl_os_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        failed_tests = [test['name'] for test in
                        before_result if 'passed' not in test['outcome']]
        # STEP #5
        show_step(5)
        openstack_actions.warm_restart_nodes('mon01')
        # STEP #6
        show_step(6)
        sl_os_deployed.check_prometheus_targets(mon_nodes)
        # STEP #7
        show_step(7)
        # Run SL component tetsts
        after_result = sl_os_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        for test in after_result:
            if test['name'] not in failed_tests:
                assert 'passed' in test['outcome'], \
                    'Failed test {}'.format(test)
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.sl_deployed)
    def test_warm_shutdown_mon01_node(self, openstack_actions,
                                      sl_os_deployed,
                                      show_step):
        """Test warm shutdown mon01

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check LMA before mon node shutdown
            5. Shutdown mon01 node
            6. Run LMA tests after failover


        """
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        mon_nodes = sl_os_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))
        sl_os_deployed.check_prometheus_targets(mon_nodes)
        before_result = sl_os_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        failed_tests = [test['name'] for test in
                        before_result if 'passed' not in test['outcome']]
        # STEP #5
        show_step(5)
        openstack_actions.warm_shutdown_openstack_nodes('mon01')
        # STEP #6
        show_step(6)
        # Run SL component tetsts
        after_result = sl_os_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        for test in after_result:
            if test['name'] not in failed_tests:
                assert 'passed' in test['outcome'], \
                    'Failed test {}'.format(test)
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.sl_deployed)
    def test_restart_mon_with_vip(self, sl_os_deployed,
                                  openstack_actions, salt_actions,
                                  common_services_actions, show_step):
        """Test restart mon with VIP

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute and monitoring nodes
            4. Check LMA before mon node restart
            5. Find mon minion id with VIP
            6. Restart mon minion id with VIP
            7. Check that VIP was actually migrated on a new node
            8. Run tempest smoke after failover


        """
        # TR case #4753939
        common_services_actions.check_keepalived_pillar()
        salt = salt_actions

        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        mon_nodes = sl_os_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))
        before_result = sl_os_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        failed_tests = [test['name'] for test in
                        before_result if 'passed' not in test['outcome']]

        # STEP #5
        show_step(5)
        mon_vip_pillar = salt.get_pillar(
            tgt="mon0*",
            pillar="_param:cluster_vip_address")[0]
        vip = [vip for minion_id, vip in mon_vip_pillar.items()][0]
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        # STEP #6
        show_step(6)
        openstack_actions.warm_restart_nodes(minion_vip)

        # STEP #7
        show_step(7)
        # Check that VIP has been actually migrated to a new node
        new_minion_vip = common_services_actions.get_keepalived_vip_minion_id(
            vip)
        LOG.info("Migrated VIP {0} is on {1}".format(vip, new_minion_vip))
        assert new_minion_vip != minion_vip, (
            "VIP {0} wasn't migrated from {1} after node reboot!"
            .format(vip, new_minion_vip))
        common_services_actions.check_keepalived_pillar()

        # STEP #8
        show_step(8)
        # Run SL component tetsts
        after_result = sl_os_deployed.run_sl_tests_json(
            'cfg01', '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus/', 'test_alerts.py')
        for test in after_result:
            if test['name'] not in failed_tests:
                assert 'passed' in test['outcome'], \
                    'Failed test {}'.format(test)
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.openstack_deployed)
    def test_restart_ctl_with_vip(self, underlay, openstack_deployed,
                                  openstack_actions, salt_actions,
                                  common_services_actions, show_step):
        """Test restart clt with VIP

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Find controller minion id with VIP
            5. Restart controller minion id with VIP
            6. Check that VIP was actually migrated on a new node
            7. Run tempest smoke after failover


        """
        # TR case #3385671
        common_services_actions.check_keepalived_pillar()
        salt = salt_actions

        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        ctl_vip_pillar = salt.get_pillar(
            tgt="I@nova:controller:enabled:True",
            pillar="_param:cluster_vip_address")[0]
        vip = [vip for minion_id, vip in ctl_vip_pillar.items()][0]
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        # STEP #5
        show_step(5)
        openstack_actions.warm_restart_nodes(minion_vip)

        # STEP #6
        show_step(6)
        # Check that VIP has been actually migrated to a new node
        new_minion_vip = common_services_actions.get_keepalived_vip_minion_id(
            vip)
        LOG.info("Migrated VIP {0} is on {1}".format(vip, new_minion_vip))
        assert new_minion_vip != minion_vip, (
            "VIP {0} wasn't migrated from {1} after node reboot!"
            .format(vip, new_minion_vip))
        common_services_actions.check_keepalived_pillar()

        # STEP #7
        show_step(7)
        openstack_actions.run_tempest(pattern='smoke')

        LOG.info("*************** DONE **************")
