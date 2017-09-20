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

    @pytest.mark.fail_snapshot
    def test_k8s_install(self, config, show_step,
                         k8s_deployed, k8s_actions, sl_deployed, sl_actions):
        """Test for deploying MCP environment with k8s+stacklight and check it

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

        """
        # STEP #5
        show_step(5)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"
        netchecker_port = netchecker.get_service_port(k8sclient)
        show_step(6)
        netchecker.get_netchecker_pod_status(k8s=k8s_deployed,
                                             namespace='netchecker')

        show_step(7)
        netchecker.get_netchecker_pod_status(k8s=k8s_deployed,
                                             pod_name='netchecker-agent',
                                             namespace='netchecker')

        # show_step(8)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      netchecker_pod_port=netchecker_port)
        show_step(9)
        res = netchecker.get_metric(k8sclient,
                                    netchecker_pod_port=netchecker_port,
                                    namespace='netchecker')

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

        prometheus_client = sl_deployed.api
        try:
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'
                      .format(current_targets))
        except:
            LOG.warning('Restarting keepalived service on mon nodes...')
            sl_actions._salt.local(tgt='mon*', fun='cmd.run',
                                   args='systemctl restart keepalived')
            LOG.warning(
                'Ip states after forset restart {0}'.format(
                    sl_actions._salt.local(tgt='mon*',
                                           fun='cmd.run', args='ip a')))
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'
                      .format(current_targets))

        # todo (tleontovich) add assertion that k8s targets here
        for metric in metrics:
            res = prometheus_client.get_query(metric)
            for entry in res:
                assert entry["metric"]["job"] == 'kubernetes-service-endpoints'
            LOG.debug('Metric {} exists'.format(res))
            # todo (tleontovich) add asserts here and extend the tests
            # with acceptance criteria

        if config.k8s.k8s_conformance_run:
            k8s_actions.run_conformance()
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_only_k8s_install(self, config, k8s_deployed, k8s_actions):
        """Test for deploying MCP environment with k8s and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Run conformance if need

        """
        if config.k8s.k8s_conformance_run:
            k8s_actions.run_conformance()
        LOG.info("*************** DONE **************")
