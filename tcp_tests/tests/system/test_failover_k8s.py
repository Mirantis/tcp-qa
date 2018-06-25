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


class TestFailoverK8s(object):

    @pytest.mark.grap_versions
    @pytest.mark.fail_snapshot
    def test_k8s_ctl_vip_reboot(self, show_step, underlay, k8s_deployed,
                                k8s_actions, common_services_actions,
                                salt_actions):
        """Test restart clt with VIP

        Scenario:
            1. Deploy mcp with k8s ha
            2. Run conformance
            3. Check keepalived pillar configuration
            4. Find master node with assigned VIP
            5. Reboot server with VIP
            6. Check that VIP was migrated on new node
            7. Run conformance
            8. Shutdown server with VIP
            9. Check that VIP was migrated
            10. Run conformance

        """
        show_step(1)
        show_step(2)
        k8s_actions.run_conformance()

        show_step(3)
        common_services_actions.check_keepalived_pillar()

        show_step(4)
        vip = k8s_actions.get_keepalived_vip()
        LOG.info("VIP ip address: {}".format(vip))
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        show_step(5)
        k8s_actions.shutdown_node(
            k8s_actions.get_node_name_by_subname(minion_vip),
            warm=True, reboot=True)

        show_step(6)
        new_minion_vip =\
            common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("After reboot VIP {0} migrated to {1}".format(
            vip, new_minion_vip))
        assert new_minion_vip != minion_vip
        minion_vip = new_minion_vip

        show_step(7)
        k8s_actions.run_conformance()

        show_step(8)
        k8s_actions.shutdown_node(
            k8s_actions.get_node_name_by_subname(new_minion_vip),
            warm=False, reboot=False)

        show_step(9)
        LOG.info("After shutdown VIP {0} migrated to {1}".format(
            vip, new_minion_vip))
        new_minion_vip =\
            common_services_actions.get_keepalived_vip_minion_id(vip)
        assert new_minion_vip != minion_vip

        show_step(10)
        k8s_actions.run_conformance()
