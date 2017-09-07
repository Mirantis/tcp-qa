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
import os
import pytest

from tcp_tests import logger

LOG = logger.logger


@pytest.mark.deploy
class Test_Mcp11_install(object):
    """Test class for testing mcp11 vxlan deploy"""

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8119
    def test_mcp11_ocata_ovs_install(self, underlay, openstack_deployed,
                                          show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8119
    def test_mcp11_ocata_ovs_sl_install(self, underlay, config,
                                        openstack_deployed,
                                        sl_deployed, sl_actions, show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current targets are UP
        7. Check grafana dashboards

        """
        expected_service_list = ['monitoring_remote_storage_adapter',
                                 'monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        # STEP #4
        mon_nodes = sl_actions.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))
        for node in mon_nodes:
            services_status = sl_actions.get_service_info_from_node(node)
            assert len(services_status) == len(expected_service_list), \
                'Some services are missed on node {0}. ' \
                'Current service list {1}'.format(node, services_status)
            for service in expected_service_list:
                assert service in services_status, \
                    'Missing service {0} in {1}'.format(service, services_status)
                assert '0' not in services_status.get(service), \
                    'Service {0} failed to start'.format(service)
        prometheus_client = sl_deployed.api
        try:
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'.format(current_targets))
        except:
            LOG.info('Restarting keepalived service on mon nodes...')
            sl_actions._salt.local(tgt='mon*', fun='cmd.run',
                                   args='systemctl restart keepalived')
            LOG.warning(
                'Ip states after force restart {0}'.format(
                    sl_actions._salt.local(tgt='mon*',
                                           fun='cmd.run', args='ip a')))
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'.format(current_targets))
        # Assert that targets are up
        for entry in current_targets:
            assert 'up' in entry['health'], \
                'Next target is down {}'.format(entry)
        # Run SL component tetsts
        sl_actions.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/tests/prometheus')
        # Download report
        sl_actions.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests')
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8120
    def test_mcp11_ocata_dvr_install(self, underlay, openstack_deployed,
                                          show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8120
    def test_mcp11_ocata_dvr_sl_install(self, underlay, config,
                                        openstack_deployed,
                                        sl_deployed, sl_actions, show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current targets are UP
        7. Check grafana dashboards

        """
        expected_service_list = ['monitoring_remote_storage_adapter',
                                 'monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        # STEP #4
        mon_nodes = sl_actions.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))
        for node in mon_nodes:
            services_status = sl_actions.get_service_info_from_node(node)
            assert len(services_status) == len(expected_service_list), \
                'Some services are missed on node {0}. ' \
                'Current service list {1}'.format(node, services_status)
            for service in expected_service_list:
                assert service in services_status,\
                    'Missing service {0} in {1}'.format(service, services_status)
                assert '0' not in services_status.get(service),\
                    'Service {0} failed to start'.format(service)
        prometheus_client = sl_deployed.api
        try:
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'.format(current_targets))
        except:
            LOG.info('Restarting keepalived service on mon nodes...')
            sl_actions._salt.local(tgt='mon*', fun='cmd.run',
                                   args='systemctl restart keepalived')
            LOG.warning(
                'Ip states after force restart {0}'.format(
                    sl_actions._salt.local(tgt='mon*',
                                           fun='cmd.run', args='ip a')))
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'.format(current_targets))
        # Assert that targets are up
        for entry in current_targets:
            assert 'up' in entry['health'], \
                'Next target is down {}'.format(entry)

            # Assert that targets are up
            for entry in current_targets:
                assert 'up' in entry['health'], \
                    'Next target is down {}'.format(entry)
        # Run SL component tetsts
        sl_actions.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/tests/prometheus')
        # Download report
        sl_actions.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests')
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8117
    def test_mcp11_ocata_dpdk_install(self, underlay, openstack_deployed,
                                      show_step):
        """Test for deploying an mcp dpdk environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8117
    def test_mcp11_ocata_dvr_decapod_install(self, underlay, decapod_deployed,
                                             openstack_deployed, show_step):
        """Test for deploying an mcp dpdk environment and check it

        :type list: decapod_deployed.decapod_nodes , list of
                    config.underlay.ssh objects filtered for decapod roles.
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")
