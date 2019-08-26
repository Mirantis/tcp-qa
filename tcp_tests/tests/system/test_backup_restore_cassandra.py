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


class TestBackupRestoreCassandra(object):
    def get_cfg_fqn(self, salt):
        salt_master = salt.local("I@salt:master", "network.get_fqdn")
        return salt_master['return'][0].keys()[0]

    def update_grains_and_mine(self, salt):
        salt.run_state("I@cassandra:backup:client", "saltutil.sync_grains")
        salt.run_state("I@cassandra:backup:client", "saltutil.mine.flush")
        salt.run_state("I@cassandra:backup:client", "saltutil.mine.update")

    def create_network(self, underlay_actions, network_name, cfg_node):
        underlay_actions.check_call(
            "source /root/keystonercv3 && " +
            "openstack network create {}".format(network_name),
            node_name=cfg_node,
            raise_on_err=False)
        LOG.info('Network {} created before backup'.format(network_name))

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
            "parameters.cassandra.backup.client.restore_latest",
            "1",
            "cluster/*/infra/backup/client_cassandra.yml")
        reclass_actions.add_bool_key(
            "parameters.cassandra.backup.client.enabled",
            "True",
            "cluster/*/infra/backup/client_cassandra.yml")
        reclass_actions.add_key(
            "parameters.cassandra.backup.client.restore_from",
            "remote",
            "cluster/*/infra/backup/client_cassandra.yml")
        yield
        reclass_actions.delete_key(
            "parameters.cassandra.backup.client.restore_latest",
            "cluster/*/infra/backup/client_cassandra.yml")
        reclass_actions.delete_key(
            "parameters.cassandra.backup.client.enabled",
            "cluster/*/infra/backup/client_cassandra.yml")
        reclass_actions.delete_key(
            "parameters.cassandra.backup.client.restore_from",
            "cluster/*/infra/backup/client_cassandra.yml")

    @pytest.fixture()
    def create_instant_backup(self):

        def create(salt):
            salt.run_state("*", "saltutil.refresh_pillar")
            salt.run_state(
                "I@cassandra:backup:client or I@cassandra:backup:server",
                "state.sls salt.minion")
            self.update_grains_and_mine(salt)
            salt.run_state("I@cassandra:backup:server", "state.apply linux.system")
            salt.run_state("I@cassandra:backup:client",
                           "state.sls openssh.client,cassandra.backup")
            salt.run_state("cfg01*", "state.sls reclass")
            backup = salt.run_state(
                "I@cassandra:backup:client",
                "cmd.run",
                "bash /usr/local/bin/cassandra-backup-runner-call.sh")
            LOG.info(backup)
        return create

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_creation(self, salt_actions, show_step,
                             create_instant_backup, _):
        """ Backup Cassandra Database

        Scenario:
            1. Enable Cassandra backup. Refresh pillars on all the nodes
               (default parameters for backup)
               Apply the salt.minion state
               Refresh grains and mine for the cassandra client node
               Add a Cassandra user
               Apply required states
               Sync reclass state
               Create an instant backup
            2. Verify that a complete backup has been created
        """
        salt = salt_actions

        show_step(1)
        create_instant_backup(salt)
        show_step(2)
        backup_on_client_node = salt.run_state(
            "I@cassandra:backup:client",
            "cmd.run",
            "ls /var/backups/cassandra/full")
        assert len(backup_on_client_node[0]['return'][0].values()) > 0, \
            "Backup is not created on Cassandra client node"
        backup_on_server_node = salt.run_state(
            "I@cassandra:backup:server",
            "cmd.run",
            "ls /srv/volumes/backup/cassandra/full")
        assert len(backup_on_server_node[0]['return'][0].values()) > 0, \
            "Backup is not created on Cassandra server node"

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_restore_automatic(self, salt_actions, reclass_actions,
                               drivetrain_actions,
                               show_step, underlay_actions,
                               handle_restore_params, create_instant_backup, _
                               ):
        """ Restore Cassandra Database using Jenkins job

        Scenario:
            0. Prepare restore parameters
            1. Create network to be backuped
            2. Create an instant backup
            3. Restore from the backup. Add job class for restore Cassandra
            4. Restore from the backup. Run Jenkins job
        """
        salt = salt_actions
        reclass = reclass_actions
        dt = drivetrain_actions
        cfg_node = self.get_cfg_fqn(salt)
        fixture_network_name = "test1"
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        show_step(1)
        self.create_network(underlay_actions, fixture_network_name, cfg_node)
        show_step(2)
        create_instant_backup(salt)
        show_step(3)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.restore_cassandra",
            "cluster/*/cicd/control/leader.yml")
        salt.run_state("I@jenkins:client", "jenkins.client")
        show_step(4)
        job_name = "deploy-cassandra-db-restore"
        run_cassandra_restore = dt.start_job_on_cid_jenkins(
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            job_name=job_name)

        assert run_cassandra_restore == "SUCCESS"
        network_presented = self.is_network_restored(
            underlay_actions,
            fixture_network_name,
            cfg_node)
        assert network_presented, \
            'Network {} is not restored'.format(fixture_network_name)

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_manual(self, salt_actions,
                                   reclass_actions, show_step,
                                   underlay_actions, create_instant_backup,
                                   handle_restore_params, _,):
        """ Backup and restore Cassandra Database

        Scenario:
            0. Prepare restore parameters
            1. Create network to be backuped
            2. Create an instant backup
            3. Restore from the backup. Stop the supervisor-database service
                on the OpenContrail control nodes
            4. Restore: Remove the Cassandra files on control nodes
            5. Restore: Start the supervisor-database service on the
                Cassandra client backup node
            6. Restore: Apply the cassandra state
            7. Restore: Reboot the Cassandra backup client role node
            8. Restore: Reboot the other OpenContrail control nodes
            9. Restore: Restart the supervisor-database service
            10. Restore: verify that OpenContrail is in correct state
        """
        salt = salt_actions
        fixture_network_name = "backuptest2"
        cfg_node = self.get_cfg_fqn(salt)

        show_step(1)
        self.create_network(underlay_actions, fixture_network_name, cfg_node)
        show_step(2)
        create_instant_backup(salt)
        show_step(3)
        salt.run_state("I@cassandra:backup:client",
                       "cmd.run",
                       "I@cassandra:backup:client")
        salt.run_state("I@opencontrail:control",
                       "cmd.run",
                       "doctrail controller systemctl stop contrail-database")
        show_step(4)
        salt.run_state("I@opencontrail:control",
                       "cmd.run",
                       "rm -rf /var/lib/configdb/*")
        show_step(5)
        salt.run_state("I@opencontrail:control",
                       "cmd.run",
                       "doctrail controller systemctl start contrail-database")
        show_step(6)
        salt.run_state("I@cassandra:backup:client", "state.sls", "cassandra")
        show_step(7)
        salt.run_state("I@cassandra:backup:client", "system.reboot")
        show_step(8)
        salt.run_state(
            "I@opencontrail:control and not I@cassandra:backup:client",
            "system.reboot")
        show_step(9)
        time.sleep(60)
        salt.run_state(
            "I@opencontrail:control",
            "cmd.run",
            "doctrail controller systemctl restart contrail-database")

        show_step(10)
        time.sleep(80)
        network_presented = self.is_network_restored(
            underlay_actions,
            fixture_network_name,
            cfg_node)
        assert network_presented, \
            'Network {} is not restored'.format(fixture_network_name)
        statuses_ok = True
        failures = ''
        statuses = salt.run_state(
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
                        failures += "On node {} service {} has "\
                                    "unexpected status after restore:" \
                                    " {} \n".format(node_name,
                                                    service.strip(),
                                                    status)
        assert statuses_ok, failures
