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
from tcp_tests.helpers import netchecker

LOG = logger.logger


@pytest.mark.deploy
class Testk8sInstall(object):
    """Test class for testing Kubernetes deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cz8116
    @pytest.mark.k8s_calico_sl
    def test_k8s_install_calico_lma(self, config, show_step,
                                    k8s_deployed,
                                    stacklight_deployed):
        """Test for deploying MCP with k8s+stacklight_calico and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup stack light nodes
            5. Setup Kubernetes cluster and check it nodes
            6. Check netchecker server is running
            7. Check netchecker agent is running
            8. Check connectivity
            9. Get metrics from netchecker
            10. Run LMA component tests
            11. Optionally run k8s e2e tests

        """

        show_step(5)
        nch = netchecker.Netchecker(k8s_deployed.api)

        show_step(6)
        nch.wait_netchecker_pods_running(netchecker.NETCHECKER_SERVER_PREFIX)

        show_step(7)
        nch.wait_netchecker_pods_running(netchecker.NETCHECKER_AGENT_PREFIX)

        show_step(8)
        nch.wait_check_network(works=True)

        show_step(9)
        res = nch.get_metric()

        assert res.status_code == 200, 'Unexpected response code {}'\
            .format(res)
        metrics = ['ncagent_error_count_total', 'ncagent_http_probe_code',
                   'ncagent_http_probe_connect_time_ms',
                   'ncagent_http_probe_connection_result',
                   'ncagent_http_probe_content_transfer_time_ms',
                   'ncagent_http_probe_dns_lookup_time_ms',
                   'ncagent_http_probe_server_processing_time_ms',
                   'ncagent_http_probe_tcp_connection_time_ms',
                   'ncagent_http_probe_total_time_ms',
                   'ncagent_report_count_tota']
        for metric in metrics:
            assert metric in res.text.strip(), \
                'Mandotory metric {0} is missing in {1}'.format(
                    metric, res.text)
        show_step(10)
        # Run SL component tests
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cz8115
    def test_k8s_install_contrail_lma(self, config, show_step,
                                      k8s_deployed,
                                      stacklight_deployed):
        """Test for deploying MCP with k8s+stacklight+contrail and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup stack light nodes
            5. Setup Kubernetes cluster and check it nodes
            6. Run LMA2.0 component tests
            7. Optionally run k8s e2e conformance

        """
        show_step(6)
        # Run SL component tests
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')

        if config.k8s.k8s_conformance_run:
            show_step(7)
            k8s_deployed.run_conformance()
        LOG.info("*************** DONE **************")

    @pytest.mark.extract(container_system='docker', extract_from='conformance',
                         files_to_extract=['report'])
    @pytest.mark.merge_xunit(path='/root/report',
                             output='/root/conformance_result.xml')
    @pytest.mark.grab_k8s_results(name=['k8s_conformance.log',
                                        'conformance_result.xml'])
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cz8116
    @pytest.mark.k8s_calico
    def test_only_k8s_install(self, config, show_step,
                              k8s_deployed, k8s_logs):
        """Test for deploying MCP environment with k8s and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Run conformance if need

        """

        if config.k8s.k8s_conformance_run:
            show_step(5)
            k8s_deployed.run_conformance()
        LOG.info("*************** DONE **************")
