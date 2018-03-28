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


class TestFailoverOpenStackServices(object):
    """Test class for testing MCP services failover"""

    def show_failed_msg(self, failed):
        return "There are failed tempest tests:\n\n  {0}".format(
            '\n\n  '.join([(name + ': ' + detail)
                           for name, detail in failed.items()]))

    def create_and_run_rally_load_task(
            self, rally, times, concurrency, timeout, raise_on_timeout=False):

        rally.create_rally_task('/root/rally/rally_load_task.json',
                                rally_load_task(times, concurrency))
        LOG.info("Running rally load task: {0} iterations with concurrency {1}"
                 ", timeout: {2} sec".format(times, concurrency, timeout))

        # Run rally task with created task file
        res = rally.run_task('/home/rally/.rally/rally_load_task.json',
                             timeout=timeout,
                             raise_on_timeout=raise_on_timeout,
                             verbose=False)
        # LOG only lines related to the task iterations,
        # skip all other setup/teardown messages
        for line in res['stdout']:
            if 'rally.task.runner' in line:
                LOG.info(line.strip())

    def get_ps_time(self, underlay, process_name, node_names):
        """Get the started datetime of the process on the specified nodes

        Returns the dict {<node_name>: <str>, } where <str> is the 'ps' output
        """
        res = {
            node_name: underlay.check_call(
                "ps -eo lstart,cmd|grep [^]]{0}".format(process_name),
                node_name=node_name, raise_on_err=False)['stdout_str']
            for node_name in node_names
        }
        return res

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="gtw01.", prepare_openstack=True)
    def test_restart_keepalived(self, func_name, underlay, config,
                                openstack_deployed,
                                common_services_actions,
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
        ps_before = self.get_ps_time(underlay, "keepalived", ctl_node_names)
        assert all(["keepalived" in p for n, p in ps_before.items()]), (
            "'keepalived' is not running on some nodes: {0}".format(ps_before))

        # STEP #1
        show_step(1)
        underlay.delayed_call(
            "salt 'ctl*' service.restart keepalived",
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        # STEP #2
        show_step(2)
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=60, concurrency=6, timeout=900)

        # STEP #3
        show_step(3)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "keepalived")
        LOG.info(ret)
        ps_after = self.get_ps_time(underlay, "keepalived", ctl_node_names)
        for node_name, ps in ps_before.items():
            assert ps_after[node_name] and (ps != ps_after[node_name]), (
                "Keepalived wasn't restarted on node {0}".format(node_name))

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
                             openstack_deployed,
                             common_services_actions,
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
        ps_before = self.get_ps_time(underlay, "keepalived", ctl_node_names)
        assert all(["keepalived" in p for n, p in ps_before.items()]), (
            "'keepalived' is not running on some nodes: {0}".format(ps_before))

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
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=60, concurrency=6, timeout=900)

        # STEP #4
        show_step(4)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "keepalived")
        LOG.info(ret)
        ps_after = self.get_ps_time(underlay, "keepalived", ctl_node_names)

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

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="gtw01.", prepare_openstack=True)
    def test_kill_keepalived(self, func_name, underlay, config,
                             openstack_deployed,
                             common_services_actions,
                             salt_actions, openstack_actions,
                             rally, show_step):
        """Test kill keepalived and haproxy on ctl node with VIP under load

        Scenario:
            1. Find controller minion id with VIP
            2. Set keepalived to be killed on the ctl node with VIP
               in few minutes, TR case #3385683
            3. Run rally task to generate load (some tasks should fail
               because of step 2)
            4. Check that keepalived was killed on the ctl node with VIP
            5. Check that SL sent a e-mail notification about the failed
                keepalived service, and then remove the VIP remaining
                on the previous VIP node during running rally task with
                load.
            6. Check that VIP was actually migrated on a new node
            7. Find controller minion id with migrated VIP
            8. Set haproxy to be killed on the ctl node with VIP
               in few minutes, TR case #4753980
            9. Run rally task to generate load (some tasks should fail
               because of step 7)
            10. Check that haproxy was killed on the ctl node with VIP
               and started again by systemd
            11. Run tempest smoke after failover
            12. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
        """
        common_services_actions.check_keepalived_pillar()
        salt = salt_actions

        ctl_node_names = underlay.get_target_node_names(
            target='ctl')

        # Keepalived case
        # STEP #1
        show_step(1)
        # Get the ps output with datetime of the process
        ps_before = self.get_ps_time(underlay, "keepalived", ctl_node_names)
        assert all(["keepalived" in p for n, p in ps_before.items()]), (
            "'keepalived' is not running on some nodes: {0}".format(ps_before))

        ctl_vip_pillar = salt.get_pillar(
            tgt="I@nova:controller:enabled:True",
            pillar="_param:cluster_vip_address")[0]
        vip = [vip for minion_id, vip in ctl_vip_pillar.items()][0]
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        # STEP #2
        show_step(2)
        underlay.delayed_call(
            "salt '{0}' cmd.run 'killall -9 keepalived'".format(minion_vip),
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        LOG.info("'at -l':\n" + underlay.check_call(
            "at -l", host=config.salt.salt_master_host)['stdout_str'])

        # STEP #3
        show_step(3)
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=60, concurrency=4, timeout=900)

        # STEP #4
        show_step(4)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "keepalived")
        LOG.info(ret)
        ps_after = self.get_ps_time(underlay, "keepalived", ctl_node_names)

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
        # TODO(ddmitriev):
        #        5. Check that SL sent a e-mail notification about the failed
        #        keepalived service, and then remove the VIP remaining
        #        on the node after killing keepalived.
        #        Alternative: check prometheus alerts list on mon*:
        #        curl http://localhost:15011/api/v1/alerts

        # Remove the VIP address manually because
        # the killed keepalived cannot do it
        underlay.delayed_call(
            "salt '{0}' cmd.run 'ip a d {1}/32 dev ens4'"
            .format(minion_vip, vip),
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=60, concurrency=4, timeout=900)

        # STEP #6
        show_step(6)
        # Check that VIP has been actually migrated to a new node
        new_minion_vip = common_services_actions.get_keepalived_vip_minion_id(
            vip)
        LOG.info("Migrated VIP {0} is on {1}".format(vip, new_minion_vip))
        assert new_minion_vip != minion_vip, (
            "VIP {0} wasn't migrated from {1} after killing keepalived!"
            .format(vip, new_minion_vip))
        common_services_actions.check_keepalived_pillar()

        # Haproxy case
        # STEP #7
        show_step(7)
        # Get the ps output with datetime of the process
        ps_before = self.get_ps_time(underlay, "haproxy", ctl_node_names)
        assert all(["haproxy" in p for n, p in ps_before.items()]), (
            "'haproxy' is not running on some nodes: {0}".format(ps_before))

        # STEP #8
        show_step(8)
        underlay.delayed_call(
            "salt '{0}' cmd.run 'killall -9 haproxy'".format(new_minion_vip),
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        LOG.info("'at -l':\n" + underlay.check_call(
            "at -l", host=config.salt.salt_master_host)['stdout_str'])

        # STEP #9
        show_step(9)
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=200, concurrency=4, timeout=1800)

        # STEP #10
        show_step(10)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "haproxy")
        LOG.info(ret)
        ps_after = self.get_ps_time(underlay, "haproxy", ctl_node_names)

        for node_name, ps in ps_before.items():
            if node_name == new_minion_vip:
                # Check that haproxy has been actually restarted
                # on <new_minion_vip> node
                assert ps_after[node_name] and (ps != ps_after[node_name]), (
                    "Haproxy wasn't restarted on node {0}: {1}"
                    .format(node_name, ps_after[node_name]))
            else:
                # Check that haproxy on other ctl nodes was not restarted
                assert ps == ps_after[node_name], (
                   "Haproxy was restarted while it shouldn't on node {0}"
                   .format(node_name))

        # STEP #11
        show_step(11)
        results = rally.run_tempest(pattern='set=smoke',
                                    report_prefix=func_name,
                                    timeout=1800)
        # Step #12
        show_step(12)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="gtw01.", prepare_openstack=True)
    def test_kill_rabbit_galera(self, func_name, underlay, config,
                                openstack_deployed,
                                common_services_actions,
                                salt_actions, openstack_actions,
                                rally, show_step):
        """Test kill rabbitmq and galera on ctl node with VIP under load

        Scenario:
            1. Find controller minion id with VIP
            2. Set rabbitmq_server to be killed on a random ctl node
               in few minutes, TR case #3385677
            3. Run rally task to generate load
            4. Check that rabbitmq_server was killed on the ctl node with VIP
            5. Find controller minion id with Galera which is receiving
               connections
            6. Set mysql server to be killed in few minutes, TR case #4753976
            7. Run rally task to generate load
            8. Check that mysql was killed and started again by systemd
            9. Check galera cluster status and replication
            10. Run tempest smoke after failover
            11. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
        """
        common_services_actions.check_keepalived_pillar()
        salt = salt_actions

        ctl_node_names = underlay.get_target_node_names(
            target='ctl')

        # Rabbitmq case
        # STEP #1
        show_step(1)
        # Get the ps output with datetime of the process
        ps_before = self.get_ps_time(
            underlay, "rabbitmq_server", ctl_node_names)
        assert all(["rabbitmq_server" in p for n, p in ps_before.items()]), (
            "'rabbitmq_server' is not running on some nodes: {0}"
            .format(ps_before))

        ctl_vip_pillar = salt.get_pillar(
            tgt="I@nova:controller:enabled:True",
            pillar="_param:cluster_vip_address")[0]
        vip = [vip for minion_id, vip in ctl_vip_pillar.items()][0]
        ctl_minions = ctl_vip_pillar.keys()
        minion_vip = common_services_actions.get_keepalived_vip_minion_id(vip)
        LOG.info("VIP {0} is on {1}".format(vip, minion_vip))

        # STEP #2
        show_step(2)

        ctl_minion = underlay.get_random_node(ctl_minions)
        ctl_node_name = salt_actions.get_grains(
            tgt=ctl_minion, grains='fqdn')[0][ctl_minion]
        LOG.info("Scheduling to kill rabbitmq on the minion {0}"
                 .format(ctl_minion))
        underlay.delayed_call(
            "salt '{0}' cmd.run 'killall -9 -u rabbitmq'".format(ctl_minion),
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        LOG.info("'at -l':\n" + underlay.check_call(
            "at -l", host=config.salt.salt_master_host)['stdout_str'])

        # STEP #3
        show_step(3)
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=60, concurrency=4, timeout=900)

        # STEP #4
        show_step(4)
        ps_after = self.get_ps_time(underlay,
                                    "rabbitmq_server",
                                    ctl_node_names)

        for node_name, ps in ps_before.items():
            if node_name == ctl_node_name:
                # Check that rabbitmq_server has been actually stopped
                # on <minion_vip> node
                assert not ps_after[node_name], (
                    "'rabbitmq_server' was not stopped on node {0}"
                    .format(minion_vip))
            else:
                # Check that rabbitmq_server on other ctl nodes
                # was not restarted
                assert ps == ps_after[node_name], (
                   "'rabbitmq_server' was restarted while it shouldn't!")

        # Mysql case
        # STEP #5
        show_step(5)
        # At first, ensure that mysql is running on all controllers
        ps_before = self.get_ps_time(
            underlay, "mysqld", ctl_node_names)
        assert all(["mysqld" in p for n, p in ps_before.items()]), (
            "'mysqld' is not running on some nodes: {0}"
            .format(ps_before))

        # Check haproxy status on the node with VIP and find the mysql backend
        # which is receiving the connections
        haproxy_status = common_services_actions.get_haproxy_status(minion_vip)
        mysql_status = haproxy_status['mysql_cluster']
        mysql_tgt = ''
        scur = 0
        for svname in mysql_status.keys():
            if svname == "FRONTEND" or svname == "BACKEND":
                continue
            snew = int(mysql_status[svname]['scur'])
            if scur < snew:
                scur = snew
                mysql_tgt = svname + '*'
        assert scur > 0, ("No sessions to 'mysql_cluster' haproxy backend on "
                          "the node with VIP, something wrong with cluster.")

        # STEP #6
        show_step(6)
        LOG.info("Scheduling to kill mysqld on the minion {0}"
                 .format(ctl_minion))
        underlay.delayed_call(
            "salt '{0}' cmd.run 'killall -9 -u mysql'".format(mysql_tgt),
            host=config.salt.salt_master_host,
            delay_min=2,
            delay_max=3)

        LOG.info("'at -l':\n" + underlay.check_call(
            "at -l", host=config.salt.salt_master_host)['stdout_str'])

        # STEP #7
        show_step(7)
        # Run rally task with created task file
        self.create_and_run_rally_load_task(
            rally, times=60, concurrency=4, timeout=900)

        # STEP #8
        show_step(8)
        ret = salt.service_status("I@nova:controller:enabled:True",
                                  "mysql")
        LOG.info(ret)
        ps_after = self.get_ps_time(underlay, "mysqld", ctl_node_names)

        for node_name, ps in ps_before.items():
            if node_name == minion_vip:
                # Check that mysql actually restarted on <minion_vip> node
                assert ps_after[node_name] and (ps != ps_after[node_name]), (
                    "Mysql wasn't restarted on node {0}: {1}"
                    .format(node_name, ps_after[node_name]))
            else:
                # Check that Mysql on other ctl nodes was not restarted
                assert ps == ps_after[node_name], (
                   "Mysql was restarted while it shouldn't on node {0}"
                   .format(node_name))

        # STEP #9
        show_step(9)
        # TODO(ddmitriev): check galera cluster status and replication
        # like it was checked in OSTF.

        # STEP #10
        show_step(10)
        results = rally.run_tempest(pattern='set=smoke',
                                    report_prefix=func_name,
                                    timeout=1800)
        # Step #11
        show_step(11)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")
