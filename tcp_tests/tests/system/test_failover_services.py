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


def rally_load_task(times=10, concurrency=2):
    return """{{
        "NovaServers.boot_and_delete_server": [
            {{
                "args": {{
                    "flavor": {{
                        "name": "m1.tiny"
                    }},
                    "image": {{
                        "name": "^cirros.*-disk$"
                    }},
                    "auto_assign_nic": true
                }},
                "runner": {{
                    "type": "constant",
                    "times": {times},
                    "concurrency": {concurrency}
                }},
                "context": {{
                    "users": {{
                        "tenants": 3,
                        "users_per_tenant": 2
                    }},
                    "network": {{
                        "start_cidr": "10.2.0.0/24",
                        "networks_per_tenant": 2
                    }}
                }}
            }}
        ]
    }}""".format(times=times, concurrency=concurrency)


class TestFailoverServices(object):
    """Test class for testing MCP services failover"""

    def show_failed_msg(self, failed):
        return "There are failed tempest tests:\n\n  {0}".format(
            '\n\n  '.join([(name + ': ' + detail)
                           for name, detail in failed.items()]))

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="gtw01.", prepare_openstack=True)
    def test_restart_keepalived(self, func_name, underlay, config,
                                openstack_deployed, common_services_actions,
                                salt_actions, openstack_actions,
                                rally, show_step):
        """Test restart keepalived on ctl* nodes

        Scenario:
            1. Set keepalived to restart on ctl* nodes in few minutes
            2. Run rally task to generate load (some tasks should fail
               because of step 2)
            3. Check that keepalived was restarted on ctl* nodes
            4. Run tempest smoke after failover
            5. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
        """
        # TR case #4756965
        common_services_actions.check_keepalived_pillar()
        salt = salt_actions

        ctl_node_names = underlay.get_target_node_names(
            target='ctl')

        # Get the ps output with datetime of the process
        ps_before = {
            node_name: underlay.check_call(
                "ps -eo lstart,cmd|grep [^]]keepalived",
                node_name=node_name)['stdout_str']
            for node_name in ctl_node_names
        }

        # STEP #1
        show_step(1)
        underlay.delayed_call(
            "salt 'ctl*' service.restart keepalived",
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        # STEP #2
        show_step(2)
        # Create a task file in the directory that will be mounted to rally
        rally.create_rally_task('/root/rally/rally_load_task.json',
                                rally_load_task(times=50, concurrency=6))
        # Run rally task with created task file
        rally.run_task('/home/rally/.rally/rally_load_task.json', timeout=900,
                       raise_on_timeout=False)

        # STEP #3
        show_step(3)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "keepalived")
        LOG.info(ret)
        ps_after = {
            node_name: underlay.check_call(
                "ps -eo lstart,cmd|grep [^]]keepalived",
                node_name=node_name)['stdout_str']
            for node_name in ctl_node_names
        }

        for node_name, ps in ps_before.items():
            assert ps != ps_after[node_name], "Keepalived wasn't restarted!"

        # STEP #4
        show_step(4)
        results = rally.run_tempest(pattern='set=smoke',
                                    report_prefix=func_name,
                                    timeout=1800)
        # Step #5
        show_step(5)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="gtw01.", prepare_openstack=True)
    def test_stop_keepalived(self, func_name, underlay, config,
                             openstack_deployed, common_services_actions,
                             salt_actions, openstack_actions,
                             rally, show_step):
        """Test stop keepalived on ctl node with VIP under load

        Scenario:
            1. Find controller minion id with VIP
            2. Set keepalived to stop on the ctl node with VIP in few minutes
            3. Run rally task to generate load (some tasks should fail
               because of step 2)
            4. Check that keepalived was stopped on the ctl node with VIP
            5. Run tempest smoke after failover
            6. Check tempest report for failed tests

            3. Run tempest smoke after failover

        Requiremets:
            - Salt cluster
            - OpenStack cluster
        """
        # TR case #3385682
        common_services_actions.check_keepalived_pillar()
        salt = salt_actions

        ctl_node_names = underlay.get_target_node_names(
            target='ctl')

        # Get the ps output with datetime of the process
        ps_before = {
            node_name: underlay.check_call(
                "ps -eo lstart,cmd|grep [^]]keepalived",
                node_name=node_name)['stdout_str']
            for node_name in ctl_node_names
        }

        # STEP #1
        show_step(1)
        ctl_vip_pillar = salt.get_pillar(
            tgt="I@nova:controller:enabled:True",
            pillar="_param:cluster_vip_address")[0]
        vip = [vip for minion_id, vip in ctl_vip_pillar.items()][0]
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        # STEP #2
        show_step(2)
        underlay.delayed_call(
            "salt '{0}' service.stop keepalived".format(minion_vip),
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        # STEP #3
        show_step(3)
        # Create a task file in the directory that will be mounted to rally
        rally.create_rally_task('/root/rally/rally_load_task.json',
                                rally_load_task(times=50, concurrency=6))
        # Run rally task with created task file
        rally.run_task('/home/rally/.rally/rally_load_task.json', timeout=900,
                       raise_on_timeout=False)

        # STEP #4
        show_step(4)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "keepalived")
        LOG.info(ret)
        ps_after = {
            node_name: underlay.check_call(
                "ps -eo lstart,cmd|grep [^]]keepalived",
                node_name=node_name, raise_on_err=False)['stdout_str']
            for node_name in ctl_node_names
        }

        for node_name, ps in ps_before.items():
            if node_name == minion_vip:
                # Check that keepalived actually stopped on <minion_vip> node
                assert not ps_after[node_name], (
                    "Keepalived was not stopped on node {0}"
                    .format(minion_vip))
            else:
                # Check that keepalived on other ctl nodes was not restarted
                assert ps == ps_after[node_name], (
                   "Keepalived was restarted while it shouldn't!")

        # STEP #5
        show_step(5)
        results = rally.run_tempest(pattern='set=smoke',
                                    report_prefix=func_name,
                                    timeout=1800)
        # Step #6
        show_step(6)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")
