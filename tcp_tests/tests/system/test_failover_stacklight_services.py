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
from devops.helpers import helpers
import pytest

from tcp_tests import logger
from tcp_tests.helpers import ext

LOG = logger.logger


class TestFailoverStacklightServices(object):
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
