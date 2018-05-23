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

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests.helpers import netchecker

LOG = logger.logger


class TestMCPCalico(object):
    """Test class for Calico network provider in k8s.
       Common calico tests requirements:
            KUBERNETES_NETCHECKER_ENABLED=true
    """

    @pytest.mark.fail_snapshot
    def test_k8s_netchecker_calico(self, show_step, config, k8s_deployed):
        """Test for deploying k8s environment with Calico plugin and check
           network connectivity between different pods by k8s-netchecker

        Scenario:
            1. Check k8s installation.
            2. Get network verification status. Excepted status is 'OK'.

        Duration: 3000 seconds
        """

        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"
        netchecker_port = netchecker.get_service_port(k8sclient)

        show_step(2)
        netchecker.wait_check_network(k8sclient, works=True, timeout=300,
                                      netchecker_pod_port=netchecker_port)

    @pytest.mark.fail_snapshot
    @pytest.mark.calico_ci
    @pytest.mark.cz8116
    def test_calico_route_recovery(self, show_step, config, underlay,
                                   k8s_deployed):
        """Test for deploying k8s environment with Calico plugin and check
           that local routes are recovered by felix after removal

        Scenario:
            1. Check k8s installation.
            2. Check netchecker-server service.
            3. Check netchecker-agent daemon set.
            4. Get network verification status. Excepted status is 'OK'.
            5. Get metrics from netchecker.
            6. Remove local route to netchecker-agent pod on the first node.
            7. Check that the route is automatically recovered.
            8. Get network verification status. Excepted status is 'OK'.

        Duration: 3000 seconds
        """

        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"
        netchecker_port = netchecker.get_service_port(k8sclient)

        show_step(2)
        netchecker.get_netchecker_pod_status(k8s=k8s_deployed,
                                             namespace='netchecker')

        show_step(3)
        netchecker.get_netchecker_pod_status(k8s=k8s_deployed,
                                             pod_name='netchecker-agent',
                                             namespace='netchecker')

        show_step(4)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      netchecker_pod_port=netchecker_port)

        show_step(5)
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
                   'ncagent_report_count_total']
        for metric in metrics:
            assert metric in res.text.strip(), \
                'Mandatory metric {0} is missing in {1}'.format(
                    metric, res.text)

        show_step(6)
        first_node = k8sclient.nodes.list()[0]
        first_node_ips = [addr.address for addr in first_node.status.addresses
                          if 'IP' in addr.type]
        assert len(first_node_ips) > 0, "Couldn't find first k8s node IP!"
        first_node_names = [name for name in underlay.node_names()
                            if name.startswith(first_node.name)]
        assert len(first_node_names) == 1, "Couldn't find first k8s node " \
                                           "hostname in SSH config!"
        first_node_name = first_node_names.pop()

        target_pod_ip = None

        for pod in k8sclient.pods.list(namespace='netchecker'):
            LOG.debug('NC pod IP: {0}'.format(pod.status.pod_ip))
            if pod.status.host_ip not in first_node_ips:
                continue
            # TODO: get pods by daemonset with name 'netchecker-agent'
            if 'netchecker-agent-' in pod.name and 'hostnet' not in pod.name:
                target_pod_ip = pod.status.pod_ip

        assert target_pod_ip is not None, "Could not find netchecker pod IP!"

        route_del_cmd = 'ip route delete {0}'.format(target_pod_ip)
        underlay.sudo_check_call(cmd=route_del_cmd, node_name=first_node_name)
        LOG.debug('Removed local route to pod IP {0} on node {1}'.format(
            target_pod_ip, first_node.name
        ))

        show_step(7)
        route_chk_cmd = 'ip route list | grep -q "{0}"'.format(target_pod_ip)
        helpers.wait_pass(
            lambda: underlay.sudo_check_call(cmd=route_chk_cmd,
                                             node_name=first_node_name),
            timeout=120,
            interval=2
        )
        pod_ping_cmd = 'sleep 120 && ping -q -c 1 -w 3 {0}'.format(
            target_pod_ip)
        underlay.sudo_check_call(cmd=pod_ping_cmd, node_name=first_node_name)
        LOG.debug('Local route to pod IP {0} on node {1} is '
                  'recovered'.format(target_pod_ip, first_node.name))

        show_step(8)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      netchecker_pod_port=netchecker_port,
                                      works=True)

    @pytest.mark.fail_snapshot
    @pytest.mark.calico_ci
    def test_calico_network_policies(self, show_step, config, underlay,
                                     k8s_deployed):
        """Test for deploying k8s environment with Calico and check
           that network policies work as expected.
           Policy test additional requirement:
                KUBERNETES_CALICO_POLICY_ENABLED=true

        Scenario:
            1. Check k8s installation.
            2. Get network verification status. Excepted status is 'OK'.
            3. Enable network isolation for 'netchecker' namespace.
            4. Allow connections to netchecker-server from tests.
            5. Get network verification status. Excepted status is 'FAIL'
               because no netcheker-agent pods should be able to reach
               netchecker-service pod.
            6. Add kubernetes network policies which allow connections
               from netchecker-agent pods (including ones with host network).
            7. Get network verification status. Excepted status is 'OK'.

        Duration: 3000 seconds
        """

        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"
        kube_master_nodes = k8s_deployed.get_k8s_masters()
        assert kube_master_nodes, "No k8s masters found in pillars!"
        netchecker_port = netchecker.get_service_port(k8sclient)

        show_step(2)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=True, timeout=300,
                                      netchecker_pod_port=netchecker_port)

        show_step(3)
        netchecker.kubernetes_block_traffic_namespace(underlay,
                                                      kube_master_nodes[0],
                                                      'netchecker')

        show_step(4)
        netchecker.calico_allow_netchecker_connections(underlay, k8sclient,
                                                       kube_master_nodes[0],
                                                       'netchecker')

        show_step(5)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=False, timeout=500,
                                      netchecker_pod_port=netchecker_port)

        show_step(6)
        netchecker.kubernetes_allow_traffic_from_agents(underlay,
                                                        kube_master_nodes[0],
                                                        'netchecker')

        show_step(7)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=True, timeout=300,
                                      netchecker_pod_port=netchecker_port)
