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
        gtw01 = [node_name for node_name in
                 underlay.node_names() if 'gtw01' in node_name]
        with underlay.remote(node_name=gtw01[0]) as gtw_remote:
            result = gtw_remote.execute('find /root -name "report_*.xml"')
            LOG.debug("Find result {0}".format(result))
            file_name = result['stdout'][0].rstrip()
            LOG.debug("Founded files {0}".format(file_name))
            gtw_remote.download(destination=file_name, target=os.getcwd())

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
        gtw01 = [node_name for node_name in
                 underlay.node_names() if 'gtw01' in node_name]
        with underlay.remote(node_name=gtw01[0]) as gtw_remote:
            result = gtw_remote.execute('find /root -name "report_*.xml"')
            LOG.debug("Find result {0}".format(result))
            file_name = result['stdout'][0].rstrip()
            LOG.debug("Founded files {0}".format(file_name))
            gtw_remote.download(destination=file_name, target=os.getcwd())

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
