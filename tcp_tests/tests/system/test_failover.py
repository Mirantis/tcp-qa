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
import time

from devops.helpers import helpers
import pytest

from tcp_tests import logger
from tcp_tests.helpers import ext

LOG = logger.logger


class TestFailover(object):
    """Test class for testing OpenStack nodes failover"""

    @staticmethod
    def check_influxdb_xfail(sl_deployed, node_name, value):

        def check_influxdb_data():
            return value in sl_deployed.check_data_in_influxdb(node_name)

        try:
            helpers.wait(
                check_influxdb_data,
                timeout=10, interval=2,
                timeout_msg=('Influxdb data {0} was not replicated to {1} '
                             '[https://mirantis.jira.com/browse/PROD-16272]'
                             .format(value, node_name)))
        except Exception:
            pytest.xfail('Influxdb data {0} was not replicated to {1} '
                         '[https://mirantis.jira.com/browse/PROD-16272]'
                         .format(value, node_name))

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
            6. Run LMA smoke after failover


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
    def test_kill_influxdb_relay_mon01_node(self, sl_os_deployed,
                                            show_step):
        """Test kill influxdb relay on mon01 node

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check LMA before mon node shutdown
            5. Kill influxdb relay on mon01 node
            6. Post data into influx
            7. Get data from all healthy nodes
            8. Start influx db
            9. Request data on mon01
            10. Run LMA tests after fail and compare with result before fail


        """
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
        sl_os_deployed.kill_sl_service_on_node('mon01', 'influxdb-relay')

        # STEP #6
        show_step(6)
        sl_os_deployed.post_data_into_influx('mon02')

        # STEP #7
        show_step(7)
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon02')
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon03')

        # STEP #8
        show_step(8)
        sl_os_deployed.start_service('mon01', 'influxdb-relay')

        # STEP #9
        show_step(9)
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon01')

        # STEP #10
        show_step(10)
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
    def test_kill_influxdb_mon01_node(self, sl_os_deployed, show_step):
        """Test kill influxdb on mon01 node

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check LMA before mon node shutdown
            5. Kill influxdb on mon01 node
            6. Post data into influx
            7. Get data from all healthy nodes
            8. Start influx db
            9. Request data on mon01
            10. Run LMA tests after fail and compare with result before fail


        """
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
        sl_os_deployed.kill_sl_service_on_node('mon01', 'influxd')

        # STEP #6
        show_step(6)
        sl_os_deployed.post_data_into_influx('mon02')

        # STEP #7
        show_step(7)
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon02')
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon03')

        # STEP #8
        show_step(8)
        sl_os_deployed.start_service('mon01', 'influxd')

        # STEP #9
        show_step(9)
        self.check_influxdb_xfail(sl_os_deployed, 'mon01', 'mymeas')

        # STEP #10
        show_step(10)
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
    def test_stop_influxdb_relay_mon_nodes(self, sl_os_deployed,
                                           show_step):
        """Test stop influxdb relay on mon01 node

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check LMA before mon node shutdown
            5. Stop influxdb relay on mon01 and mon02 nodes
            6. Post data into influx
            7. Get data from all healthy nodes
            8. Start influx db
            9. Request data on mon01, 02
            10. Run LMA tests after fail and compare with result before fail


        """
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
        sl_os_deployed.stop_sl_service_on_node('mon01', 'influxdb-relay')
        sl_os_deployed.stop_sl_service_on_node('mon02', 'influxdb-relay')

        # STEP #6
        show_step(6)
        sl_os_deployed.post_data_into_influx('mon03')

        # STEP #7
        show_step(7)
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon03')

        # STEP #8
        show_step(8)
        sl_os_deployed.start_service('mon01', 'influxdb-relay')
        sl_os_deployed.start_service('mon02', 'influxdb-relay')

        # STEP #9
        show_step(9)
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon01')
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon02')

        # STEP #10
        show_step(10)
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
    def test_stop_influxdb_mon_nodes(self, sl_os_deployed, show_step):
        """Test stop influxdb on mon01 node

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute, monitoring nodes
            4. Check LMA before mon node shutdown
            5. Stop influxdb on mon01 and mon02 node
            6. Post data into influx
            7. Get data from all healthy nodes
            8. Start influx db
            9. Request data on mon01
            10. Run LMA tests after fail and compare with result before fail


        """
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
        sl_os_deployed.stop_sl_service_on_node('mon01', 'influxdb')
        sl_os_deployed.stop_sl_service_on_node('mon02', 'influxdb')

        # STEP #6
        show_step(6)
        sl_os_deployed.post_data_into_influx('mon03')

        # STEP #7
        show_step(7)
        assert 'mymeas' in sl_os_deployed.check_data_in_influxdb('mon03')

        # STEP #8
        show_step(8)
        sl_os_deployed.start_service('mon01', 'influxdb')
        sl_os_deployed.start_service('mon02', 'influxdb')

        # STEP #9
        show_step(9)
        self.check_influxdb_xfail(sl_os_deployed, 'mon01', 'mymeas')
        self.check_influxdb_xfail(sl_os_deployed, 'mon02', 'mymeas')

        # STEP #10
        show_step(10)
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
    @pytest.mark.revert_snapshot("sl_deployed")
    def test_mcp11_ocata_ovs_sl_kill_prometheus_service(self, underlay, config,
                                                        openstack_deployed,
                                                        sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        8. Kill prometheus server service
        10. Check current prometheus targets are UP
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        11. Run SL component tests
        12. Download SL component tests report
        """

        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]
        LOG.info("Prometheus server nodes - {}".format(p_nodes))

        sl_deployed._salt.local(
            tgt=p_nodes[0],
            fun='cmd.run',
            args=["kill -9 $(pidof /opt/prometheus/prometheus)"]
        )

        sl_deployed.check_prometheus_targets(mon_nodes)

        LOG.info("Wait 10 sec for recover Prometheus server".format(p_nodes))
        time.sleep(10)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        assert len(p_nodes) == 2, "Prometheus server didn't recover while 10 sec"  # noqa

        sl_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.revert_snapshot("sl_deployed")
    def test_mcp11_ocata_ovs_sl_kill_prometheus_container(self, underlay,
                                                          config,
                                                          openstack_deployed,
                                                          sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Kill prometheus server container
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        11. Run SL component tests
        12. Download SL component tests report
        """
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'  # noqa
                }
            })['return'][0]
        p_nodes_names = [n for n in p_nodes if len(p_nodes[n]) > 0]
        LOG.info("Prometheus server nodes - {}".format(p_nodes_names))

        container_id = p_nodes[p_nodes_names[0]].keys()[0]

        r = sl_deployed._salt.local(
            tgt=p_nodes_names[0],
            fun='dockerng.kill',
            args=["{}".format(container_id)]
        )['return'][0]

        assert r[p_nodes_names[0]]['result'], "Killing prometheus container failed" # noqa

        sl_deployed.check_prometheus_targets(mon_nodes)

        LOG.info("Wait 10 sec for recover Prometheus server".format(p_nodes))
        time.sleep(10)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        assert len(p_nodes) == 2, "Prometheus server didn't recover while 10 sec"  # noqa

        sl_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.revert_snapshot("sl_deployed")
    def test_mcp11_ocata_ovs_sl_poweroff_prometheus_node(self, underlay,
                                                         config,
                                                         openstack_deployed,
                                                         sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Power off node with prometheus server
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        8. Power on node with prometheus server
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        11. Run SL component tests
        12. Download SL component tests report
        """
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'  # noqa
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        underlay.sudo_check_call(cmd="poweroff -f", node_name=p_nodes[0])

        sl_deployed.check_prometheus_targets(mon_nodes)

        LOG.info("Wait 60 sec for recover Prometheus server".format(p_nodes))
        time.sleep(60)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        assert len(p_nodes) == 2, "Prometheus server didn't recover while 60 sec"  # noqa

        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")
