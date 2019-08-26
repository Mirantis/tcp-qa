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
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestBackupRestoreCassandra(object):
    # ToDo: compute it dynamically
    cfg_node = "cfg01.heat-cicd-queens-contrail41-sl.local"

    def create_network(self, underlay_actions, network_name):
        underlay_actions.check_call(
            "source /root/keystonercv3 && "
            "openstack network create {}".format(network_name),
            node_name=self.cfg_node,
            raise_on_err=False)

    def verify_network_exists(self, underlay_actions, network_name):
        underlay_actions.check_call(
            "source /root/keystonercv3 && "
            "openstack network list --name {}".format(network_name),
            node_name=self.cfg_node,
            raise_on_err=False)["stdout"]

    def add_restore_params(self, show_step, reclass):
        show_step(9)
        reclass.add_key(
            "parameters.cassandra.backup.client.restore_latest",
            "1",
            "cluster/*/infra/backup/client_cassandra.yml")
        reclass.add_bool_key(
            "parameters.cassandra.backup.client.enabled",
            "True",
            "cluster/*/infra/backup/client_cassandra.yml")
        reclass.add_key(
            "parameters.cassandra.backup.client.restore_from",
            "remote",
            "cluster/*/infra/backup/client_cassandra.yml")

    def prepare_and_create_backup(self, salt, show_step):
        show_step(1)
        salt.run_state("*", "saltutil.refresh_pillar")
        show_step(2)
        salt.run_state(
            "I@cassandra:backup:client or I@cassandra:backup:server",
            "state.sls salt.minion")
        show_step(3)
        salt.run_state("I@cassandra:backup:client", "saltutil.sync_grains")
        salt.run_state("I@cassandra:backup:client", "saltutil.mine.flush")
        salt.run_state("I@cassandra:backup:client", "saltutil.mine.update")
        show_step(4)
        salt.run_state("I@cassandra:backup:server", "state.apply linux.system")
        show_step(5)
        salt.run_state("I@cassandra:backup:client",
                       "state.sls openssh.client,cassandra.backup")
        show_step(6)
        salt.run_state("I@cassandra:backup:server", "state.sls cassandra")
        show_step(7)
        salt.run_state("cfg01*", "state.sls reclass")
        show_step(8)
        backup = salt.run_state(
            "ntw01*",
            "cmd.run",
            "bash /usr/local/bin/cassandra-backup-runner-call.sh")
        LOG.info(backup)

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_automatic(self, salt_actions, reclass_actions,
                                      show_step, underlay_actions, _):
        """ Backup and restore Cassandra Database using Jenkins job

        Scenario:
            1. Enable Cassandra backup. Refresh pillars on all the nodes
               (default parameters for backup)
            2. Apply the salt.minion state
            3. Refresh grains and mine for the cassandra client node
            4. Add a Cassandra user
            5. Apply required state on the cassandra client nodes
            6. Apply required state on the cassandra server nodes
            7. Sync reclass state
            8. Create an instant backup
            9. Restore from the backup. Prepare parameters
            10. Restore from the backup. Add job class for restore Cassandra
            11. Restore from the backup. Run Jenkins job
        """
        salt = salt_actions
        reclass = reclass_actions
        fixture_network_name = "test1"
        jenkins_creds = salt.get_cluster_jenkins_creds()
        jenkins_url = jenkins_creds.get("url")
        jenkins_user = jenkins_creds.get("user")
        jenkins_pass = jenkins_creds.get("pass")
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        self.prepare_and_create_backup(salt, show_step)
        self.create_network(underlay_actions, fixture_network_name)

        self.add_restore_params(show_step, reclass)
        show_step(10)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.restore_cassandra",
            "cluster/*/cicd/control/leader.yml")
        salt.run_state("I@jenkins:client", "jenkins.client")
        show_step(11)
        job_name = "deploy-cassandra-db-restore"
        run_cassandra_restore = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=False,
            job_name=job_name)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number="lastBuild")

        LOG.info(description)
        LOG.info("\n".join(stages))

        assert run_cassandra_restore == "SUCCESS", "{0}\n{1}".format(
            description, "\n".join(stages))
        self.verify_network_exists(underlay_actions, fixture_network_name)

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_manual(self, salt_actions,
                                   reclass_actions,
                                   show_step, underlay_actions, _):
        """ Backup and restore Cassandra Database

        Scenario:
            1. Enable Cassandra backup. Refresh pillars on all the nodes
               (default parameters for backup)
            2. Apply the salt.minion state
            3. Refresh grains and mine for the cassandra client node
            4. Add a Cassandra user
            5. Apply required state on the cassandra client nodes
            6. Apply required state on the cassandra server nodes
            7. Sync reclass state
            8. Create an instant backup
            9. Restore: Stop the supervisor-database service
               on the OpenContrail control nodes
            10. Restore from the backup. Add job class for restore Cassandra
            11. Restore: Remove the Cassandra files on control nodes
            12. Restore: Start the supervisor-database service on the
                Cassandra client backup node:
            13. Restore: Apply the cassandra state
            14. Restore: Reboot the Cassandra backup client role node
            15. Restore: Reboot the other OpenContrail control nodes
            16. Restore: Restart the supervisor-database service
            17. Restore: verify that OpenContrail is in correct state
        """
        salt = salt_actions
        reclass = reclass_actions
        fixture_network_name = "backuptest2"
        self.create_network(underlay_actions, fixture_network_name)
        self.prepare_and_create_backup(salt, show_step)
        self.add_restore_params(show_step, reclass)
        show_step(10)
        salt.run_state("I@opencontrail:control",
                       "cmd.run",
                       "doctrail controller systemctl stop contrail-database")
        show_step(11)
        salt.run_state("I@opencontrail:control",
                       "cmd.run",
                       "rm -rf /var/lib/configdb/*")
        show_step(12)
        salt.run_state("I@cassandra:backup:client",
                       "cmd.run",
                       "doctrail controller systemctl stop contrail-database")
        show_step(13)
        salt.run_state("I@opencontrail:control",
                       "cmd.run",
                       "doctrail controller systemctl start contrail-database")
        show_step(14)
        salt.run_state("I@cassandra:backup:client", "cmd.run")
        show_step(15)
        salt.run_state("I@cassandra:backup:client", "system.reboot")
        show_step(16)
        time.sleep(60)
        salt.run_state(
            "I@opencontrail:control",
            "cmd.run",
            "doctrail controller systemctl restart contrail-database")
        self.verify_network_exists(underlay_actions, fixture_network_name)
        show_step(17)
        time.sleep(60)
        statuses_ok = True
        failures = ''
        statuses = salt.run_state(
            "I@opencontrail:control",
            "cmd.run",
            "doctrail controller contrail-status")

        for node_name, statuses_output in statuses[0]["return"][0].iteritems():
            for status_line in statuses_output.splitlines():
                if not status_line.startswith("=="):
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
