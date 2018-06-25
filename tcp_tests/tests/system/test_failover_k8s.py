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
                                      k8s_actions, common_services_actions,
                                      config):
        """Test restart and shutdown master with VIP

        Scenario:
            1. Deploy mcp with k8s ha
            2. Check keepalived pillar configuration
            3. Find master node with assigned VIP
            4. Reboot server with VIP
            5. Check that VIP was migrated
            6. Check api server availability
        """
        show_step(1)
        show_step(2)
        common_services_actions.check_keepalived_pillar()

        show_step(3)
        vip = k8s_actions.get_keepalived_vip()
        LOG.info("VIP ip address: {}".format(vip))
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        show_step(4)
        k8s_actions.shutdown_node(minion_vip, warm=False, reboot=False)

        show_step(5)
        try:
            new_minion_vip =\
                common_services_actions.get_keepalived_vip_minion_id(vip)
        except Exception as e:
            if "expected on a single node" in e.message:
                LOG.info("Waiting 10s (default keepalived check interval)")
                time.sleep(10)
                new_minion_vip = \
                    common_services_actions.get_keepalived_vip_minion_id(vip)
            else:
                raise e
        LOG.info("VIP {0} migrated to {1}".format(vip, new_minion_vip))
        assert new_minion_vip != minion_vip

        show_step(6)
        assert "apiVersion" in underlay.check_call(
            cmd="curl -k -s 'https://{}'".format(vip),
            host=config.salt.salt_master_host, raise_on_err=False)
