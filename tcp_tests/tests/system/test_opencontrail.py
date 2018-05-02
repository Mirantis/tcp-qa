#    Copyright 2016 Mirantis, Inc.
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
class TestOpenContrail(object):
    """Test class for testing OpenContrail on a TCP lab"""

    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="ctl01.")
    def test_opencontrail(self, config, underlay, salt_actions,
                          openstack_deployed, show_step, sl_deployed):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Run tempest
            5. Exporting results
            6. Check docker services
            7. Check prometheus targets
            8. Run SL tests
            9. Download sl tests report
        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_deployed.run_tempest(target='ctl01',
                                           pattern=settings.PATTERN)
            openstack_deployed.download_tempest_report(stored_node='ctl01')

        expected_service_list = ['monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        prometheus_relay_enabled = salt_actions.get_pillar(
            tgt=mon_nodes[0],
            pillar="prometheus:relay:enabled")[0]
        if not prometheus_relay_enabled:
            # InfluxDB is used if prometheus relay service is not installed
            expected_service_list.append('monitoring_remote_storage_adapter')
        show_step(6)
        sl_deployed.check_docker_services(mon_nodes, expected_service_list)
        show_step(7)
        sl_deployed.check_prometheus_targets(mon_nodes)
        show_step(8)
        # Run SL component tetsts
        if settings.RUN_SL_TESTS:
            sl_deployed.run_sl_functional_tests(
                'ctl01',
                '/root/stacklight-pytest/stacklight_tests/',
                'tests/prometheus',
                'test_alerts.py')
            show_step(9)
            # Download report
            sl_deployed.download_sl_test_report(
                'ctl01',
                '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")
