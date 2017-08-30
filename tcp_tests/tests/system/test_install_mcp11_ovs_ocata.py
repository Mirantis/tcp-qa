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
    def test_mcp11_ocata_dvr_sl_install(self, underlay, openstack_deployed,
                                        sl_deployed, sl_actions, show_step):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check expected targets are ok
        7. Check grafana dashboards

        """
        LOG.info("*************** DONE **************")
        expected_service_list = ['monitoring_remote_storage_adapter',
                                 'monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        # STEP #4
        show_step(4)
        mon_nodes = [node_name for
                     node_name in underlay.node_names()
                     if 'mon' in node_name]
        show_step(5)
        for node in mon_nodes:
            service_stat_dict = {}
            with underlay.remote(node_name=node) as node_remote:
                result = node_remote.execute(
                    "docker service ls --format '{{.Name}}:{{.Replicas}}'")
                LOG.debug("Service ls result {0} "
                          "from node {1}".format(result, node))
                formatted_res = result['stdout'].splitlines()
                for line in formatted_res:
                    tmp = line.split(':')
                    service_stat_dict.update({tmp[0]: tmp[1]})
                assert len(service_stat_dict) == len(expected_service_list), \
                    'Some services are mossied on node {0}. ' \
                    'Current service list {1}'.format(node, service_stat_dict)
                for service in expected_service_list:
                    assert service in service_stat_dict,\
                        'Missing service {0} in {1}'.format(
                            service, service_stat_dict)
                    assert '0' not in service_stat_dict.get(service),\
                        'Service {0} failed to start'.format(service)
        show_step(6)
        prometheus_client = sl_deployed.api
        try:
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'.format(current_targets))
        except:
            LOG.warning('Restarting keepalived service on mon nodes...')
            sl_actions._salt.local(tgt='mon*', fun='cmd.run',
                                   args='systemctl restart keepalived')
            LOG.warning(
                'Ip states after force restart {0}'.format(
                    sl_actions._salt.local(tgt='mon*',
                                           fun='cmd.run', args='ip a')))
            current_targets = prometheus_client.get_targets()
            LOG.debug('Current targets after install {0}'.format(current_targets))


    @pytest.mark.fail_snapshot
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
