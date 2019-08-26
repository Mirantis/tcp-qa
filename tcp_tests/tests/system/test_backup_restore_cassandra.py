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
import yaml

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestBackupRestoreCassandra(object):
    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_cassandra(self, salt_actions, reclass_actions,
                                      show_step, underlay_actions, _):
        """ Backup and restore Cassandra Database

        Scenario:
            1. Enable Cassandra backup. Refresh pillars on all the nodes 
               (default backup parameters for backup)
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
        jenkins_creds = salt.get_cluster_jenkins_creds()
        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800
        # ToDo: should we get it another way?
        cfg_node = "cfg01.heat-cicd-queens-contrail41-sl.local"
        ntw_node = "ntw01.heat-cicd-queens-contrail41-sl.local"
        ntw_node_test = salt.run_state('I@cassandra:backup:client', 'test.ping')
        LOG.info('!!!!!')
        LOG.info(ntw_node_test)
        LOG.info(yaml.load(ntw_node_test))

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

        underlay_actions.check_call(
            node_name=ntw_node, verbose=False,
            cmd="/usr/local/bin/cassandra-backup-runner-call.sh")
        # kvm03.heat-cicd-queens-contrail41-sl.local or
        # salt - C 'I@cassandra:backup:server'  test.ping

        # ssh kvm03 (get IP from previous command) and check output of
        # ls /srv/volumes/backup/cassandra/full
        # ToDo: change database somehow
        ssh.check_call("source /root/keystonercv3",
                       node_name=cfg_node,
                       raise_on_err=False)['stdout_str']
        test_network_list = ssh.check_call("openstack network list",
                                           node_name=cfg_node,
                                           raise_on_err=False)['stdout_str']
        test_network_list = ssh.check_call("openstack network list"
                                           node_name=cfg_node,
                                           raise_on_err=False)['stdout_str']
        LOG.info(test_network_list)
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
        show_step(10)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.restore_cassandra",
            "cluster/*/cicd/control/leader.yml")
        salt.run_state("I@jenkins:client", "jenkins.client")
        show_step(11)
        job_name = 'deploy-cassandra-db-restore'
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
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert run_cassandra_restore == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))
