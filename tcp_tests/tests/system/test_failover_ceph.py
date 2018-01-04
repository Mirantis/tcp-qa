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


class TestFailoverCeph(object):
    """Test class for testing MCP ceph failover"""

    def get_ceph_health(self, underlay, node_names):
        """Get ceph health on the specified nodes

        Returns the dict {<node_name>: <str>, } where <str> is the 'ceph -s' output
        """
        res = {
            node_name: underlay.check_call("ceph -s",
                                           node_name=node_name,
                                           raise_on_err=False)['stdout_str']
            for node_name in node_names
        }
        return res

    def show_failed_msg(self, failed):
        return "There are failed tempest tests:\n\n  {0}".format(
            '\n\n  '.join([(name + ': ' + detail)
                           for name, detail in failed.items()]))

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="gtw01.", prepare_openstack=True)
    def test_restart_osd_node(self, func_name, underlay, config,
                              openstack_deployed, ceph_deployed,
                              common_services_actions,
                              salt_actions, openstack_actions,
                              rally, show_step):
        """Test restart ceph osd node

        Scenario:
            1. Find ceph osd nodes
            2. Check ceph health before restart
            3. Restart 1 ceph osd node
            4. Check ceph health after restart
            5. Run tempest smoke after failover
            6. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
            - Ceph cluster
        """
        # STEP #1
        show_step(1)
        osd_node_names = underlay.get_target_node_names(
            target='osd')

        # STEP #2
        show_step(2)
        # Get the ceph health output before restart
        health_before = self.get_ceph_health(underlay, osd_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_before))

        # STEP #3
        show_step(3)
        openstack_actions.warm_restart_nodes('osd01')

        # STEP #4
        show_step(4)
        # Get the ceph health output after restart
        health_after = self.get_ceph_health(underlay, osd_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Cepp health is not ok from node: {0}".format(health_after))

        # STEP #5
        show_step(5)
        results = rally.run_tempest(pattern='set=smoke',
                                    report_prefix=func_name,
                                    timeout=1800)
        # Step #6
        show_step(6)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")