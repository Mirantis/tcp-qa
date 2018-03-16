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

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_cookied_ocata_ovs_install(self, underlay, openstack_deployed,
                                       show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        if settings.RUN_TEMPEST:
            openstack_deployed.run_tempest(pattern=settings.PATTERN)
            openstack_deployed.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_cookied_ocata_dvr_install(self, underlay, openstack_deployed,
                                       show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        if settings.RUN_TEMPEST:
            openstack_deployed.run_tempest(pattern=settings.PATTERN)
            openstack_deployed.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_cookied_ocata_cicd_oss_install(self, underlay, salt_actions,
                                            openstack_deployed,
                                            oss_deployed, sl_deployed,
                                            show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup CICD nodes
        3. Setup OpenStack
        4. Setup StackLight v2
        5. Run Tempest for OpenStack cluster
        6. Get monitoring nodes
        7. Check that docker services are running
        8. Check current prometheus targets are UP
        9. Run SL component tests
        10. Download SL component tests report
        """
        show_step(5)
        if settings.RUN_TEMPEST:
            openstack_deployed.run_tempest(pattern=settings.PATTERN)
            openstack_deployed.download_tempest_report()

        expected_service_list = ['monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        show_step(6)
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        show_step(7)
        prometheus_relay_enabled = salt_actions.get_pillar(
            tgt=mon_nodes[0],
            pillar="prometheus:relay:enabled")[0]
        if not prometheus_relay_enabled:
            # InfluxDB is used if prometheus relay service is not installed
            expected_service_list.append('monitoring_remote_storage_adapter')

        sl_deployed.check_docker_services(mon_nodes, expected_service_list)

        show_step(8)
        sl_deployed.check_prometheus_targets(mon_nodes)

        show_step(9)
        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/tests/prometheus')

        show_step(10)
        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests')
        LOG.info("*************** DONE **************")
