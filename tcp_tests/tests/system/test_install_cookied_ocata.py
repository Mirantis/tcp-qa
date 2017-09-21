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


@pytest.mark.deploy
class Test_Mcp11_install(object):
    """Test class for testing mcp11 vxlan deploy"""

    @pytest.mark.fail_snapshot
    def test_cookied_ocata_ovs_install(self, underlay, openstack_deployed,
                                       show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_cookied_ocata_dvr_install(self, underlay, openstack_deployed,
                                       show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_cookied_ocata_cicd_oss_install(self, underlay, oss_deployed,
                                            openstack_deployed, sl_deployed,
                                            show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup CICD nodes
        3. Setup OpenStack
        4. Setup StackLight v2
        5. Get monitoring nodes
        6. Check that docker services are running
        7. Check current prometheus targets are UP
        8. Run SL component tests
        9. Download SL component tests report
        """
        expected_service_list = ['monitoring_remote_storage_adapter',
                                 'monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        show_step(5)
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        show_step(6)
        sl_deployed.check_docker_services(mon_nodes, expected_service_list)

        show_step(7)
        sl_deployed.check_prometheus_targets(mon_nodes)

        show_step(8)
        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/tests/prometheus')

        show_step(9)
        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests')
        LOG.info("*************** DONE **************")
