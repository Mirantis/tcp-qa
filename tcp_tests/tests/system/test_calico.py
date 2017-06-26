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
    """Test class for Calico network provider in k8s"""

    @pytest.mark.fail_snapshot
    def test_k8s_netchecker_calico(self, show_step, config, k8s_deployed):
        """Test for deploying k8s environment with Calico plugin and check
           network connectivity between different pods by k8s-netchecker

        Scenario:
            1. Install k8s with Calico network plugin.
            2. Run netchecker-server service.
            3. Run netchecker-agent daemon set.
            4. Get network verification status. Check status is 'OK'.

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        netchecker.start_server(k8s=k8s_deployed, config=config)
        netchecker.wait_check_network(k8sclient, works=True,
                                      timeout=300)

        # STEP #3
        show_step(3)
        netchecker.start_agent(k8s=k8s_deployed, config=config)

        # STEP #4
        show_step(4)
        netchecker.wait_check_network(k8sclient, works=True,
                                      timeout=300)

    @pytest.mark.fail_snapshot
    def test_calico_route_recovery(self, show_step, config, underlay,
                                   k8s_deployed):
        """Test for deploying k8s environment with Calico plugin and check
           that local routes are recovered by felix after removal

        Scenario:
            1. Install k8s with Calico network plugin.
            2. Run netchecker-server service.
            3. Run netchecker-agent daemon set.
            4. Get network verification status. Check status is 'OK'.
            5. Remove local route to netchecker-agent pod on the first node
            6. Check that the route is automatically recovered
            7. Get network verification status. Check status is 'OK'.

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        netchecker.start_server(k8s=k8s_deployed, config=config)
        LOG.info("Waiting for netchecker server is running")
        netchecker.wait_check_network(k8sclient, works=True,
                                      timeout=300)

        # STEP #3
        show_step(3)
        netchecker.start_agent(k8s=k8s_deployed, config=config)

        # STEP #4
        show_step(4)
        netchecker.wait_check_network(k8sclient, works=True,
                                      timeout=300)

        # STEP #5
        show_step(5)
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

        for pod in k8sclient.pods.list():
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

        # STEP #6
        show_step(6)
        route_chk_cmd = 'ip route list | grep -q "{0}"'.format(target_pod_ip)
        helpers.wait_pass(
            lambda: underlay.sudo_check_call(cmd=route_chk_cmd,
                                             node_name=first_node_name),
            timeout=30,
            interval=1
        )
        pod_ping_cmd = 'sleep 3 && ping -q -c 1 -w 3 {0}'.format(target_pod_ip)
        underlay.sudo_check_call(cmd=pod_ping_cmd, node_name=first_node_name)
        LOG.debug('Local route to pod IP {0} on node {1} is '
                     'recovered'.format(target_pod_ip, first_node.name))

        # STEP #7
        show_step(7)
        netchecker.wait_check_network(k8sclient, works=True)

    @pytest.mark.fail_snapshot
    def test_calico_network_policies(self, show_step, config, underlay,
                                     k8s_deployed):
        """Test for deploying k8s environment with Calico and check
           that network policies work as expected

        Scenario:
            1. Install k8s.
            2. Create new namespace 'netchecker'
            3. Run netchecker-server service
            4. Check that netchecker-server returns '200 OK'
            5. Run netchecker-agent daemon set in default namespace
            6. Get network verification status. Check status is 'OK'
            7. Enable network isolation for 'netchecker' namespace
            8. Allow connections to netchecker-server from tests using
               Calico policy
            9. Get network verification status. Check status is 'FAIL' because
               no netcheker-agent pods can reach netchecker-service pod
            10. Add kubernetes network policies which allow connections
               from netchecker-agent pods (including ones with host network)
            11. Get network verification status. Check status is 'OK'

        Duration: 3000 seconds
        """

        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"
        kube_master_nodes = k8s_deployed.get_k8s_masters()
        assert kube_master_nodes, "No k8s masters found in pillars!"

        show_step(2)
        k8s_deployed.check_namespace_create(name='netchecker')

        show_step(3)
        netchecker.start_server(k8s=k8s_deployed, config=config,
                                namespace='netchecker')

        show_step(4)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=True)

        show_step(5)
        netchecker.start_agent(k8s=k8s_deployed, config=config,
                               namespace='default',
                               service_namespace='netchecker')

        show_step(6)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=True, timeout=300)

        show_step(7)
        netchecker.kubernetes_block_traffic_namespace(underlay,
                                                      kube_master_nodes[0],
                                                      'netchecker')

        show_step(8)
        netchecker.calico_allow_netchecker_connections(underlay,
                                                       kube_master_nodes[0],
                                                       config.k8s.kube_host,
                                                       'netchecker')

        show_step(9)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=False, timeout=500)

        show_step(10)
        netchecker.kubernetes_allow_traffic_from_agents(underlay,
                                                        kube_master_nodes[0],
                                                        'netchecker')

        show_step(11)
        netchecker.wait_check_network(k8sclient, namespace='netchecker',
                                      works=True, timeout=300)
