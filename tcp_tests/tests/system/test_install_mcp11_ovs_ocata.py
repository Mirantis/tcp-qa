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
from tcp_tests import settings

LOG = logger.logger


@pytest.mark.deploy
class Test_Mcp11_install(object):
    """Test class for testing mcp11 vxlan deploy"""

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8119
    def test_mcp11_ocata_ovs_install(self, underlay,
                                     openstack_deployed,
                                     openstack_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8119
    def test_mcp11_ocata_ovs_sl_install(self, underlay, config,
                                        openstack_deployed,
                                        sl_deployed, show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Download SL component tests report
        """
        expected_service_list = ['monitoring_remote_storage_adapter',
                                 'monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        show_step(4)
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        show_step(5)
        sl_deployed.check_docker_services(mon_nodes, expected_service_list)

        show_step(6)
        sl_deployed.check_prometheus_targets(mon_nodes)

        show_step(7)
        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        show_step(8)
        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests')
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8120
    def test_mcp11_ocata_dvr_install(self,
                                     underlay,
                                     openstack_deployed,
                                     openstack_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8120
    def test_mcp11_ocata_dvr_sl_install(self, underlay, config,
                                        openstack_deployed,
                                        sl_deployed, show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Download SL component tests report
        """
        expected_service_list = ['monitoring_remote_storage_adapter',
                                 'monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        show_step(4)
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        show_step(5)
        sl_deployed.check_docker_services(mon_nodes, expected_service_list)

        show_step(6)
        sl_deployed.check_prometheus_targets(mon_nodes)

        show_step(7)
        # Run SL component tests
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        show_step(8)
        # Download report
        sl_deployed.download_sl_test_report(
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
