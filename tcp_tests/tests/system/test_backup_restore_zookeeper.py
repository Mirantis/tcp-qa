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

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestBackupRestoreZooKeeper(object):
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

    def create_backup(self, salt, show_step):
        show_step(1)
        salt.run_state("*", "saltutil.refresh_pillar")
        show_step(2)
        salt.run_state(
            "I@zookeeper:backup:client or I@zookeeper:backup:server",
            "state.sls salt.minion")
        show_step(3)
        salt.run_state("I@zookeeper:backup:client", "saltutil.sync_grains")
        salt.run_state("I@zookeeper:backup:client", "saltutil.mine.flush")
        salt.run_state("I@zookeeper:backup:client", "saltutil.mine.update")
        show_step(4)
        salt.run_state("I@zookeeper:backup:client",
                       " state.sls openssh.client,zookeeper.backup")
        show_step(5)
        salt.run_state("I@zookeeper:backup:server", "zookeeper.backup")
        show_step(6)
        backup = salt.run_state(
            "ntw01*",
            "cmd.run",
            "bash /usr/local/bin/zookeeper-backup-runner.sh")
        LOG.info(backup)

    def add_restore_params(self, show_step, reclass):
        show_step(7)
        reclass.add_key(
            "parameters._param.zookeeper.backup.client.restore_latest",
            "1",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.add_bool_key(
            "parameters._param.zookeeper.backup.client.enabled",
            "True",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.add_key(
            "parameters._param.zookeeper.backup.client.restore_from",
            "remote",
            "cluster/*/infra/backup/client_zookeeper.yml")

    def salt_cmd_on_control(self, salt, cmd):
        salt.run_state("I@opencontrail:control", "cmd.run", cmd)

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_zookeeper(self, salt_actions, reclass_actions,
                                      underlay_actions, show_step, _):
        """ Backup and restore ZooKeeper Database

        Scenario:
            1. Refresh pillars on all the nodes
            2. Apply the salt.minion state
            3. Refresh grains and mine for the ZooKeeper client node
            4. Apply required state on the ZooKeeper client nodes
            5. Apply required state on the ZooKeeper server nodes
            6. Create an instant backup
            7. Restore from the backup. Prepare parameters
            8. Restore from the backup. Add job class for restore ZooKeeper
            9. Restore from the backup. Run Jenkins job
        """
        salt = salt_actions
        reclass = reclass_actions
        fixture_network_name = "testzoo1"
        jenkins_creds = salt.get_cluster_jenkins_creds()
        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        self.create_network(underlay_actions, fixture_network_name)
        self.create_backup(salt, show_step)
        self.add_restore_params(show_step, reclass)
        show_step(8)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.restore_zookeeper",
            "cluster/*/cicd/control/leader.yml")
        salt.run_state("I@jenkins:client", "jenkins.client")

        show_step(9)
        job_name = 'deploy-zookeeper-restore'
        run_zookeeper_restore = run_jenkins_job.run_job(
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
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert run_zookeeper_restore == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))
        self.verify_network_exists(underlay_actions, fixture_network_name)

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_zookeeper_manually(self, salt_actions,
                                               reclass_actions, show_step,
                                               underlay_actions, _):
        """ Backup and restore ZooKeeper Database manually

        Scenario:
            1. Refresh pillars on all the nodes
            2. Apply the salt.minion state
            3. Refresh grains and mine for the ZooKeeper client node
            4. Apply required state on the ZooKeeper client nodes
            5. Apply required state on the ZooKeeper server nodes
            6. Create an instant backup
            7. Restore. Prepare parameters
            8. Restore. Stop the config services on control nodes
            9. Restore. Stop the control services on control nodes
            10. Restore. Stop the zookeeper service on controller nodes
            11. Restore. Remove the ZooKeeper files from the controller nodes
            12. Restore. Run the zookeeper state
            13. Restore. Start the zookeeper service on the controller nodes
            14. Restore. Start the config services on the controller nodes
            15. Restore. Start the control services on control nodes
        """
        s = salt_actions
        reclass = reclass_actions
        fixture_network_name = "testzoo2"
        self.create_network(underlay_actions, fixture_network_name)
        self.create_backup(s, show_step)
        self.add_restore_params(show_step, reclass)
        show_step(8)
        cmd = "doctrail controller systemctl {} {}"
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-api"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-schema"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-svc-monitor"))
        self.salt_cmd_on_control(s, cmd.format("stop",
                                               "contrail-device-manager"))
        self.salt_cmd_on_control(s, cmd.format("stop",
                                               "contrail-config-nodemgr"))

        show_step(9)
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-control"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-named"))
        self.salt_cmd_on_control(s, cmd.format("stop", "contrail-dns"))
        self.salt_cmd_on_control(s, cmd.format("stop",
                                               "contrail-control-nodemgr"))
        show_step(10)
        self.salt_cmd_on_control(s,
                                 "doctrail controller service zookeeper stop")
        show_step(11)
        self.salt_cmd_on_control(
            s,
            "rm -rf /var/lib/config_zookeeper_data/version-2/*")
        show_step(12)
        self.salt_cmd_on_control(s, "state.apply zookeeper.backup")
        show_step(13)
        self.salt_cmd_on_control(s,
                                 "doctrail controller service zookeeper start")
        show_step(14)
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-api"))
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-schema"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-svc-monitor"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-device-manager"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-config-nodemgr"))
        show_step(15)
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-control"))
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-named"))
        self.salt_cmd_on_control(s, cmd.format("start", "contrail-dns"))
        self.salt_cmd_on_control(s, cmd.format("start",
                                               "contrail-control-nodemgr"))
        show_step(16)
        time.sleep(60)
        self.verify_network_exists(underlay_actions, fixture_network_name)
        # ToDo: verify result of this command
        self.salt_cmd_on_control(s, "doctrail controller contrail-status")
