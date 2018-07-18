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
import time

from tcp_tests import logger

LOG = logger.logger


class TestFailoverK8s(object):

    @pytest.mark.grap_versions
    @pytest.mark.fail_snapshot
    def test_k8s_master_vip_migration(self, show_step, k8s_deployed, underlay,
                                      k8s_actions, core_actions,
                                      config, hardware):
        """Test restart and shutdown master with VIP

        Scenario:
            1. Deploy mcp with k8s ha
            2. Check keepalived pillar configuration
            3. Find master node with assigned VIP
            4. Reboot server with VIP
            5. Check that VIP was migrated
            6. Check keepalived pillar configuration
            7. Check api server availability
            8. Run conformance on node with VIP
        """
        show_step(1)
        show_step(2)
        core_actions.check_keepalived_pillar()

        show_step(3)
        vip = k8s_actions.get_keepalived_vip()
        LOG.info("VIP ip address: {}".format(vip))
        minion_vip = core_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        show_step(4)
        hardware.warm_restart_nodes(underlay, minion_vip)

        show_step(5)
        try:
            new_minion_vip =\
                core_actions.get_keepalived_vip_minion_id(vip)
        except Exception:
                time.sleep(15)
                new_minion_vip = \
                    core_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} migrated to {1}".format(vip, new_minion_vip))
        assert new_minion_vip != minion_vip

        show_step(6)
        core_actions.check_keepalived_pillar()

        show_step(7)
        curl_output = ''.join(underlay.check_call(
            cmd="curl -k -s 'https://{}'".format(vip),
            host=config.salt.salt_master_host, raise_on_err=False)['stdout'])
        assert "apiVersion" in curl_output

        show_step(8)
        k8s_actions.run_conformance(node_name=new_minion_vip)
