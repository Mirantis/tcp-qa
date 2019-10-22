#    Copyright 2019 Mirantis, Inc.
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
from tcp_tests import settings

LOG = logger.logger


class TestBackupRestoreZooKeeper(object):
    def get_cfg_fqn(self, salt):
        salt_master = salt.local("I@salt:master", "network.get_fqdn")
        return salt_master['return'][0].keys()[0]

    def create_network(self, underlay_actions, network_name, cfg_node):
        underlay_actions.check_call(
            "source /root/keystonercv3 && "
            "openstack network create {}".format(network_name),
            node_name=cfg_node,
            raise_on_err=False)

    def is_network_restored(self, underlay_actions, network_name, cfg_node):
        get_net_by_name = underlay_actions.check_call(
            "source /root/keystonercv3 && " +
            "openstack network list --name {}".format(network_name),
            node_name=cfg_node,
            raise_on_err=False)["stdout"]
        return get_net_by_name != ['\n']

    @pytest.fixture()
    def handle_restore_params(self, reclass_actions):
        reclass_actions.add_key(
            "parameters._param.zookeeper.backup.client.restore_latest",
            "1",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass_actions.add_bool_key(
            "parameters._param.zookeeper.backup.client.enabled",
            "True",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass_actions.add_key(
            "parameters._param.zookeeper.backup.client.restore_from",
            "remote",
            "cluster/*/infra/backup/client_zookeeper.yml")
        yield
        reclass_actions.delete_key(
            "parameters._param.zookeeper.backup.client.restore_latest",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass_actions.delete_key(
            "parameters._param.zookeeper.backup.client.enabled",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass_actions.delete_key(
            "parameters._param.zookeeper.backup.client.restore_from",
            "cluster/*/infra/backup/client_zookeeper.yml")

    def salt_cmd_on_control(self, salt, cmd):
        salt.run_state("I@opencontrail:control", "cmd.run", cmd)

    def update_mine_and_grains(self, salt):
        salt.run_state("I@zookeeper:backup:client", "saltutil.sync_grains")
        salt.run_state("I@zookeeper:backup:client", "saltutil.mine.flush")
        salt.run_state("I@zookeeper:backup:client", "saltutil.mine.update")

    def get_leader_node(self, salt):
        contrail_leader = salt.local(
            "I@opencontrail:control",
            "cmd.run",
            "echo stat | nc localhost 2181 | grep leader")
        result = contrail_leader['return'][0]
        for node, leader in result.iteritems():
            if leader == u'Mode: leader':
                return node
        return None

    @pytest.fixture()
    def create_instant_backup(self):

        def create(salt, leader):
            salt.run_state("*", "saltutil.refresh_pillar")
            salt.run_state(
                "I@zookeeper:backup:client or I@zookeeper:backup:server",
                "state.sls salt.minion")
            self.update_mine_and_grains(salt)
            salt.run_state("I@zookeeper:backup:client",
                           " state.sls openssh.client,zookeeper.backup")
            salt.run_state("I@zookeeper:backup:server", "zookeeper.backup")
            backup = salt.run_state(
                leader,
                "cmd.run",
                "bash /usr/local/bin/zookeeper-backup-runner.sh")
            LOG.info(backup)
        return create

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_creation(self, salt_actions, show_step,
                             create_instant_backup, _):
        """ Backup ZooKeeper Database
           Scenario:
               1. Refresh pillars on all the nodes
                  Apply the salt.minion state
                  Refresh grains and mine for the ZooKeeper client node
                  Apply required state on the ZooKeeper client nodes
                  Apply required state on the ZooKeeper server nodes
                  Create an instant backup
              2. Verify that a complete backup has been created

        """
        salt = salt_actions
        leader = self.get_leader_node(salt)
        show_step(1)
        create_instant_backup(salt, leader)
        show_step(2)
        backup_on_leader_node = salt.run_state(
            leader,
            "cmd.run",
            "ls /var/backups/zookeeper/full")
        LOG.info(backup_on_leader_node)
        assert len(backup_on_leader_node[0]['return'][0].values()) > 0, \
            "Backup is not created on ZooKeeper leader node"
        backup_on_server_node = salt.run_state(
            "I@zookeeper:backup:server",
            "cmd.run",
            "ls /srv/volumes/backup/zookeeper/full")
        LOG.info(backup_on_server_node)
        assert len(backup_on_server_node[0]['return'][0].values()) > 0, \
            "Backup is not created on ZooKeeper server node"

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_restore_zookeeper_with_job(self, salt_actions, reclass_actions,
                                        drivetrain_actions, underlay_actions,
                                        show_step, create_instant_backup,
                                        handle_restore_params, _):
        """ Restore ZooKeeper Database with Jenkins job

        Scenario:
            0. Restore from the backup. Prepare parameters
            1. Create network to be backuped
            2. Create an instant backup
            3. Restore from the backup. Add job class for restore ZooKeeper
            4. Restore from the backup. Run Jenkins job
        """
        salt = salt_actions
        reclass = reclass_actions
        dt = drivetrain_actions
        fixture_network_name = "testzoo1"
        cfg_node = self.get_cfg_fqn(salt)
        leader = self.get_leader_node(salt)
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800
        show_step(1)
        self.create_network(underlay_actions, fixture_network_name, cfg_node)
        show_step(2)
        create_instant_backup(salt, leader)
        show_step(3)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.restore_zookeeper",
            "cluster/*/cicd/control/leader.yml")
        salt.run_state("I@jenkins:client", "jenkins.client")

        show_step(4)
        job_name = 'deploy-zookeeper-restore'
        run_zookeeper_restore = dt.start_job_on_cid_jenkins(
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            job_name=job_name)
        assert run_zookeeper_restore == 'SUCCESS'
        network_presented = self.is_network_restored(
            underlay_actions,
            fixture_network_name,
            cfg_node)
        assert network_presented, \
            'Network {} is not restored'.format(fixture_network_name)

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_restore_zookeeper_manually(self, salt_actions,
                                        show_step,
                                        underlay_actions,
                                        create_instant_backup,
                                        handle_restore_params, _):
        """Restore ZooKeeper Database manually

        Scenario:
            0. Restore from the backup. Prepare parameters
            1. Create network to be backuped
            2. Create an instant backup
            3. Restore. Stop the config services on control nodes
            4. Restore. Stop the control services on control nodes
            5. Restore. Stop the zookeeper service on controller nodes
            6. Restore. Remove the ZooKeeper files from the controller nodes
            7. Restore. Run the zookeeper state
            8. Restore. Start the zookeeper service on the controller nodes
            9. Restore. Start the config services on the controller nodes
            10. Restore. Start the control services on control nodes
            11. Restore. Verify that OpenContrail is in correct state
        """
        s = salt_actions
        fixture_network_name = "testzoo2"
        leader = self.get_leader_node(s)
        cfg_node = self.get_cfg_fqn(s)
        self.create_network(underlay_actions,
                            fixture_network_name,
                            cfg_node)
        show_step(1)
        self.create_network(underlay_actions, fixture_network_name, cfg_node)
        show_step(2)
        create_instant_backup(s, leader)
        show_step(3)
        cmd = "doctrail controller systemctl {} {}"
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-api"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-schema"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-svc-monitor"))
        self.salt_cmd_on_control(s, cmd.format("stop",
                                               "contrail-device-manager"))
        self.salt_cmd_on_control(s, cmd.format("stop",
                                               "contrail-config-nodemgr"))

        show_step(4)
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-control"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-named"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-dns"))
        self.salt_cmd_on_control(s, cmd.format("stop",
                                               "contrail-control-nodemgr"))
        show_step(5)
        self.salt_cmd_on_control(s,
                                 "doctrail controller service zookeeper stop")
        show_step(6)
        self.salt_cmd_on_control(
            s,
            "rm -rf /var/lib/config_zookeeper_data/version-2/*")
        show_step(7)
        s.run_state("I@opencontrail:control",
                    "cmd.run",
                    "rm /var/backups/zookeeper/dbrestored")
        s.run_state("I@opencontrail:control", "state.apply",
                    "zookeeper.backup")
        show_step(8)
        self.salt_cmd_on_control(s,
                                 "doctrail controller service zookeeper start")
        show_step(9)
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-api"))
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-schema"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-svc-monitor"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-device-manager"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-config-nodemgr"))
        show_step(10)
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-control"))
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-named"))
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-dns"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-control-nodemgr"))
        show_step(11)
        time.sleep(60)
        network_presented = self.is_network_restored(
            underlay_actions,
            fixture_network_name,
            cfg_node)
        assert network_presented, \
            'Network {} is not restored'.format(fixture_network_name)
        statuses_ok = True
        failures = ''
        statuses = s.run_state(
            "I@opencontrail:control",
            "cmd.run",
            "doctrail controller contrail-status")

        for node_name, statuses_output in statuses[0]["return"][0].iteritems():
            for status_line in statuses_output.splitlines():
                if not status_line.startswith("==") and status_line != '':
                    service, status = status_line.split(':')
                    status = status.strip()
                    if status not in ["active", "backup"]:
                        statuses_ok = False
                        failures += "On node {} service {} has " \
                                    "unexpected status after restore:" \
                                    " {} \n".format(node_name,
                                                    service.strip(),
                                                    status)
        assert statuses_ok, failures
