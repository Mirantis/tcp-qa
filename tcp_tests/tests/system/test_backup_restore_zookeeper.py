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
    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_zookeeper(self, salt_actions, reclass_actions,
                                      show_step, underlay_actions, _):
        """ Backup and restore ZooKeeper Database

        Scenario:
            1. Enable ZooKeeper backup. Configure the ZooKeeper server role
            2. Enable ZooKeeper backup. Configure the ZooKeeper client role
            3. Refresh pillars on all the nodes
            4. Apply the salt.minion state
            5. Refresh grains and mine for the ZooKeeper client node
            6. Apply required state on the ZooKeeper client nodes
            7. Apply required state on the ZooKeeper server nodes
            8. Create an instant backup
            9. Restore from the backup. Prepare parameters
            10. Restore from the backup. Add job class for restore ZooKeeper
            11. Restore from the backup. Run Jenkins job
        """
        salt = salt_actions
        reclass = reclass_actions
        jenkins_creds = salt.get_cluster_jenkins_creds()
        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800
        # ToDo: should we get it another way?
        # salt - C 'I@opencontrail:control' cmd.run 'echo stat |
        # nc localhost 2181 | grep leader'
        ntw_node = "ntw01.heat-cicd-queens-contrail41-sl.local"

        show_step(1)
        reclass.add_bool_key("parameters.zookeeper.backup.server.enabled",
                             "True",
                             "cluster/*/infra/backup/server.yml")
        reclass.add_key("parameters.zookeeper.backup.server.hours_before_full",
                        "24",
                        "cluster/*/infra/backup/server.yml")
        reclass.add_key(
            "parameters.zookeeper.backup.server.full_backups_to_keep",
            "5",
            "cluster/*/infra/backup/server.yml")
        reclass.add_bool_key("parameters.zookeeper.backup.server.cron",
                             "True",
                             "cluster/*/infra/backup/server.yml")

        reclass.add_key("parameters.zookeeper.backup.server.backup_dir",
                        "/srv/volumes/backup/zookeeper",
                        "cluster/*/infra/backup/server.yml")
        show_step(2)
        reclass.add_bool_key("parameters.zookeeper.backup.cron",
                             "True",
                             "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.add_bool_key("parameters.zookeeper.backup.client.enabled",
                             "True",
                             "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.add_key("parameters.zookeeper.backup.client.hours_before_full",
                        "24",
                        "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.add_key(
            "parameters.zookeeper.backup.client.full_backups_to_keep",
            "5",
            "cluster/*/infra/backup/client_zookeeper.yml")
        reclass.add_key("parameters.zookeeper.backup.server.containers",
                        "- opencontrail_controller_1",
                        "cluster/*/infra/backup/client_zookeeper.yml")
        # verify zookeeper_remote_backup_server?!
        # salt ntw01*' pillar.get _param: zookeeper_remote_backup_server
        # OR
        # salt 'cfg01*' pillar.get _param: infra_kvm_node03_address

        show_step(3)
        salt.run_state("*", "saltutil.refresh_pillar")
        show_step(4)
        salt.run_state(
            "I@zookeeper:backup:client or I@zookeeper:backup:server",
            "state.sls salt.minion")
        show_step(5)
        salt.run_state("I@zookeeper:backup:client", "saltutil.sync_grains")
        salt.run_state("I@zookeeper:backup:client", "saltutil.mine.flush")
        salt.run_state("I@zookeeper:backup:client", "saltutil.mine.update")
        show_step(6)
        salt.run_state("I@zookeeper:backup:client",
                       " state.sls openssh.client,zookeeper.backup")
        show_step(7)
        salt.run_state("I@zookeeper:backup:server", "zookeeper.backup")


        # salt.run_state("cfg01*", "state.sls reclass")
        # underlay.check_call(
        #     node_name=cfg_node, verbose=verbose,
        #     cmd="salt-call state.sls reclass")
        show_step(8)

        underlay_actions.check_call(
            node_name=ntw_node, verbose=False,
            cmd="/usr/local/bin/zookeeper-backup-runner.sh")
        # kvm03.heat-cicd-queens-contrail41-sl.local or
        # salt - C 'I@zookeeper:backup:server'  test.ping

        # ssh kvm03 (get IP from previous command) and check output of
        # ls /srv/volumes/backup/zookeeper/full
        # ToDo: change database somehow
        show_step(9)
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
        show_step(10)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.restore_zookeeper",
            "cluster/*/cicd/control/leader.yml")
        salt.run_state("I@jenkins:client", "jenkins.client")
        show_step(11)
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
