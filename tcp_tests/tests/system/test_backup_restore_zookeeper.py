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


class TestBackupRestoreZooKeeper(object):
    def get_cfg_fqn(self, salt):
        salt_master = salt.local("I@salt:master", "test.ping")
        return salt_master['return'][0].keys()[0]

    def create_network(self, underlay_actions, network_name, cfg_node):
        underlay_actions.check_call(
            "source /root/keystonercv3 && "
            "openstack network create {}".format(network_name),
            node_name=cfg_node,
            raise_on_err=False)

    def verify_network_exists(self, underlay_actions, network_name, cfg_node):
        get_net_by_name = underlay_actions.check_call(
            "source /root/keystonercv3 && " +
            "openstack network list --name {}".format(network_name),
            node_name=cfg_node,
            raise_on_err=False)["stdout"]
        assert get_net_by_name != ['\n'],\
            'Network {} is not restored'.format(network_name)

    def add_restore_params(self, show_step, reclass):
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

    def remove_restore_params(self, reclass):
        reclass.delete_key(
            "parameters._param.zookeeper.backup.client.restore_latest",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.delete_key(
            "parameters._param.zookeeper.backup.client.enabled",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.delete_key(
            "parameters._param.zookeeper.backup.client.restore_from",
            "cluster/*/infra/backup/client_zookeeper.yml")

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
        cfg_node = self.get_cfg_fqn(salt)
        jenkins_creds = salt.get_cluster_jenkins_creds()
        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        self.create_network(underlay_actions, fixture_network_name, cfg_node)
        show_step(1)
        salt.run_state("*", "saltutil.refresh_pillar")
        show_step(2)
        salt.run_state(
            "I@zookeeper:backup:client or I@zookeeper:backup:server",
            "state.sls salt.minion")
        show_step(3)
        self.update_mine_and_grains(salt)
        show_step(4)
        salt.run_state("I@zookeeper:backup:client",
                       " state.sls openssh.client,zookeeper.backup")
        show_step(5)
        salt.run_state("I@zookeeper:backup:server", "zookeeper.backup")
        show_step(6)
        leader = self.get_leader_node(salt)
        backup = salt.run_state(
            leader,
            "cmd.run",
            "bash /usr/local/bin/zookeeper-backup-runner.sh")
        LOG.info(backup)
        show_step(7)
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
        self.verify_network_exists(underlay_actions,
                                   fixture_network_name,
                                   cfg_node)

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
            16. Restore. Verify that OpenContrail is in correct state
        """
        s = salt_actions
        reclass = reclass_actions
        fixture_network_name = "testzoo2"
        cfg_node = self.get_cfg_fqn(s)
        self.create_network(underlay_actions,
                            fixture_network_name,
                            cfg_node)
        self.remove_restore_params(reclass)
        show_step(1)
        s.run_state("*", "saltutil.refresh_pillar")
        show_step(2)
        s.run_state(
            "I@zookeeper:backup:client or I@zookeeper:backup:server",
            "state.sls",
            "salt.minion")
        show_step(3)
        self.update_mine_and_grains(s)
        show_step(4)
        s.run_state("I@zookeeper:backup:client",
                    "state.sls",
                    "openssh.client,zookeeper.backup")
        show_step(5)
        s.run_state("I@zookeeper:backup:server",
                    "state.sls",
                    "zookeeper.backup")
        show_step(6)
        leader = self.get_leader_node(s)
        backup = s.run_state(
            leader,
            "cmd.run",
            "bash /usr/local/bin/zookeeper-backup-runner.sh")
        LOG.info(backup)
        show_step(7)
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
        s.run_state("I@opencontrail:control", "state.apply",
                    "zookeeper.backup")
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
        self.verify_network_exists(underlay_actions,
                                   fixture_network_name,
                                   cfg_node)
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
