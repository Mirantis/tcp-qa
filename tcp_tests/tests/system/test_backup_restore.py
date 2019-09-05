#    Copyright 2018 Mirantis, Inc.
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

from devops.helpers import helpers
from devops.helpers.proc_enums import ExitCodes

from tcp_tests import logger
from tcp_tests.managers import backup_restore_manager
from tcp_tests import settings
from tcp_tests.utils import get_jenkins_job_stages
from tcp_tests.utils import run_jenkins_job

LOG = logger.logger


class TestBackupRestoreMaster(object):
    """Test class for testing backup restore of master node"""

    ENV_NAME = settings.ENV_NAME

    BCKP_SERVER_DIR = "/srv/volumes/backup/backupninja"
    RECLASS_DIR = "/srv/salt/reclass"
    FILES_TO_DELETE = [
        "nodes/_generated/log02.{}.local.yml".format(ENV_NAME),
        "classes/cluster/{}/stacklight/telemetry.yml".format(ENV_NAME),
        "classes/service/barbican",
        "classes/system/prometheus/alertmanager/container.yml"
    ]
    FILES_TO_UPDATE = [
        "nodes/_generated/mtr02.{}.local.yml".format(ENV_NAME),
        "classes/cluster/{}/ceph/rgw.yml".format(ENV_NAME),
        "classes/system/grafana/client/single.yml"
    ]

    BACKUP_JOB_NAME = 'backupninja_backup'
    BACKUP_JOB_PARAMETERS = {
        "ASK_CONFIRMATION": False
    }
    RESTORE_JOB_NAME = 'backupninja_restore'
    JENKINS_START_TIMEOUT = 60
    JENKINS_BUILD_TIMEOUT = 60 * 30

    def delete_old_backup(self, ssh, server, client):
        """Remove previous backup and/or restore flag files

        If exist, remove existing backup(s) form backup server.
        If exist, remove '/srv/salt/master-restored' and
        '/srv/salt/minion-restored' flag files, which indicate that Salt master
        backup restore procedure has already been executed.

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param server: string, backup server node where backup is stored
        :param client: string, backup client node where restore flags reside
        """
        # Delete old backups, if any, from backup server
        path = "{}/{}".format(self.BCKP_SERVER_DIR, client)
        ssh.check_call(
            "rm -rf {}".format(path), node_name=server, raise_on_err=False)

        # Delete restore flag files from backup client, if exist
        for f in ("minion-restored", "master-restored"):
            ssh.check_call(
                "rm /srv/salt/{}".format(f),
                node_name=client,
                raise_on_err=False)

    def check_salt_master_backup(self, ssh, server, path, client):
        """Check that data directories exist in backup on backup server

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param server: string, backup server node where backup is stored
        :param path: string, path to backupninja inventory of backups on server
        :param client: string, backup client node name, which indicates the
            name of backup on backup server
        """
        for subdir in ("etc", "srv", "var"):
            cmd = "test -d {}/{}/{}".format(path, client, subdir)
            result = ssh.check_call(
                cmd, node_name=server, raise_on_err=False)['exit_code']
            assert result == ExitCodes.EX_OK, (
                "'{}' data from Salt master is not in backup.".format(subdir))

    def delete_reclass_files(self, ssh, client):
        """Delete several reclass files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are deleted
        """
        files_to_delete = " ".join(self.FILES_TO_DELETE)
        ssh.check_call(
            "cd {}; rm {}".format(self.RECLASS_DIR, files_to_delete),
            node_name=client,
            raise_on_err=False)

    def update_reclass_files(self, ssh, client):
        """Update several reclass files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are updated
        :return: dict, key-value pairs of files and their hashes before update
        """
        hashes = {}
        for f in self.FILES_TO_UPDATE:
            path = "{}/{}".format(self.RECLASS_DIR, f)
            # Calculate hash of a file
            hashes[f] = ssh.check_call(
                "sha1sum {} | awk '{{print $1}}'".format(path),
                node_name=client,
                raise_on_err=False)['stdout']
            # Update a file with a dummy string
            ssh.check_call(
                "echo '{}' >> {}".format("#" * 200, path),
                node_name=client,
                raise_on_err=False)
        return hashes

    def update_backup_schedule(self, reclass):
        """Update backup schedule on backupninja client

        :param reclass: ReclassManager, tcp-qa Reclass-tools manager
        """
        path = "cluster/*/infra/config/init.yml"
        reclass.add_bool_key("parameters.backupninja.enabled", "True", path)
        reclass.add_key(
            "parameters.backupninja.client.backup_times.minute",
            "\"'*/10'\"",
            path)

    def run_jenkins_job(
            self, creds, name, parameters, start_timeout, build_timeout):
        """Execute a Jenkins job with provided parameters

        :param creds: dict, Jenkins url and user credentials
        :param name: string, Jenkins job to execute
        :param parameters: dict, parameters for Jenkins job
        :parameter start_timeout: int, timeout to wait until build is started
        :parameter build_timeout: int, timeout to wait until build is finished
        :return: tuple, Jenkins job build execution status, high level
            description of the build and verbose decription of executed job
            stages
        """
        jenkins_url, jenkins_user, jenkins_pass = (
            creds['url'], creds['user'], creds['pass'])
        build_status = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=start_timeout,
            build_timeout=build_timeout,
            verbose=False,
            job_name=name,
            job_parameters=parameters)

        description, stages = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=name,
            build_number='lastBuild')

        return build_status, description, stages

    def verify_restored_data(self, ssh, client, hashes):
        """Verify restore of deleted and updated reclass files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are updated
        :param hashes: dict, key-value pairs of files and their hashes
            before update
        """
        # Verify that deleted files are restored
        for f in self.FILES_TO_DELETE:
            path = "{}/{}".format(self.RECLASS_DIR, f)
            result = ssh.check_call(
                "test -f {}".format(path),
                node_name=client,
                raise_on_err=False)['exit_code']
            assert result == ExitCodes.EX_OK, (
                "'{}' data is not in restored on Salt master.".format(path))
        # Verify that changed files are restored
        for f in self.FILES_TO_UPDATE:
            path = "{}/{}".format(self.RECLASS_DIR, f)
            f_hash = ssh.check_call(
                "sha1sum {} | awk '{{print $1}}'".format(path),
                node_name=client,
                raise_on_err=False)['stdout']
            assert hashes[f] == f_hash, (
                "'{}' data is not in restored on Salt master.".format(path))

    @pytest.mark.grab_versions
    @pytest.mark.salt_master_manual_backup_restore
    def test_salt_master_manual_backup_restore(
            self, underlay_actions, salt_actions, show_step):
        """Test manual backup restore of Salt master data

        Scenario:
            1. Backup Salt master node
            2. Verify that Salt master backup is created on backupninja server
               node
            3. Delete/change some reclass data
            4. Restore the backup
            5. Verify that Salt master data backup is restored
            6. Verify that minions are responding

        Duration: ~ 3 min
        """
        salt = salt_actions
        ssh = underlay_actions

        backup_client = salt.local(
            "I@backupninja:client", "test.ping")['return'][0].keys()[0]
        backup_server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Delete old backup(s) and restore flags, if any exist
        self.delete_old_backup(ssh, backup_server, backup_client)

        # Create backup by moving local files to the 'backupninja' server
        show_step(1)
        cmd = "backupninja -n --run /etc/backup.d/200.backup.rsync"
        ssh.check_call(
            cmd, node_name=backup_client, raise_on_err=False, timeout=60 * 4)

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(2)
        self.check_salt_master_backup(
            ssh, backup_server, self.BCKP_SERVER_DIR, backup_client)

        # Simulate loss/change of some reclass data
        show_step(3)
        self.delete_reclass_files(ssh, backup_client)
        hashes = self.update_reclass_files(ssh, backup_client)

        # Restore the backup
        show_step(4)
        ssh.check_call(
            "salt-call state.sls salt.master.restore,salt.minion.restore",
            node_name=backup_client,
            raise_on_err=False,
            timeout=60 * 4)

        # Verify that all pieces of lost/changed data are restored
        show_step(5)
        self.verify_restored_data(ssh, backup_client, hashes)

        # Ping minions
        show_step(6)
        salt.local('*', "test.ping", timeout=30)

    @pytest.mark.grab_versions
    @pytest.mark.salt_master_manual_backup_restore_pipeline
    def test_salt_master_manual_backup_restore_pipeline(
            self, underlay_actions, salt_actions, show_step):
        """Test manual backup restore of Salt master data using DT pipeline

        Scenario:
            1. Execute 'backupninja_backup' pipeline to backup Salt
               master node
            2. Verify that Salt master backup is created on backupninja server
               node
            3. Delete/change some reclass data
            4. Restore the backup
            5. Verify that Salt master data backup is restored
            6. Verify that minions are responding

        Duration: ~ 3 min
        """
        salt = salt_actions
        ssh = underlay_actions

        backup_client = salt.local(
            "I@backupninja:client", "test.ping")['return'][0].keys()[0]
        backup_server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Delete old backup(s) and restore flags, if any exist
        self.delete_old_backup(ssh, backup_server, backup_client)

        # Execute 'backupninja_backup' pipeline to create a backup
        show_step(1)
        jenkins_creds = salt.get_cluster_jenkins_creds()
        status, description, stages = self.run_jenkins_job(
            jenkins_creds,
            self.BACKUP_JOB_NAME,
            self.BACKUP_JOB_PARAMETERS,
            self.JENKINS_START_TIMEOUT,
            self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after creating Salt master backup. "
            "Please check the build:\n{2}\n\nExecuted build "
            "stages:\n{3}".format(
                self.BACKUP_JOB_NAME, status, description, '\n'.join(stages))
        )

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(2)
        self.check_salt_master_backup(
            ssh, backup_server, self.BCKP_SERVER_DIR, backup_client)

        # Simulate loss/change of some reclass data
        show_step(3)
        self.delete_reclass_files(ssh, backup_client)
        hashes = self.update_reclass_files(ssh, backup_client)

        # Restore the backup
        show_step(4)
        status, description, stages = self.run_jenkins_job(
            jenkins_creds,
            self.RESTORE_JOB_NAME,
            None,
            self.JENKINS_START_TIMEOUT,
            self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after restoring from Salt master "
            "backup. Please check the build:\n{2}\n\nExecuted build "
            "stages:\n{3}".format(
                self.RESTORE_JOB_NAME, status, description, '\n'.join(stages))
        )

        # Verify that all pieces of lost/changed data are restored
        show_step(5)
        self.verify_restored_data(ssh, backup_client, hashes)

        # Ping minions
        show_step(6)
        salt.local('*', "test.ping", timeout=30)

    @pytest.mark.grab_versions
    @pytest.mark.salt_master_scheduled_backup_restore
    def test_salt_master_scheduled_backup_restore(
            self, underlay_actions, salt_actions, reclass_actions, show_step):
        """Test scheduled backup restore of Salt master data

        Scenario:
            1. Update Salt master backup schedule to run every 5 minutes
            2. Apply 'backupninja' state on the backupninja client node
            3. Wait until backup creation is triggered by schedule
            4. Wait until backup creation is finished
            5. Verify that Salt master backup is created on backupninja server
               node
            6. Delete/change some reclass data
            7. Restore the backup
            8. Verify that Salt master data backup is restored
            9. Verify that minions are responding

        Duration: ~ 3 min
        """
        salt = salt_actions
        ssh = underlay_actions
        reclass = reclass_actions

        backup_client = salt.local(
            "I@backupninja:client", "test.ping")['return'][0].keys()[0]
        backup_server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Delete old backup(s) and restore flags, if any exist
        self.delete_old_backup(ssh, backup_server, backup_client)

        # Re-configure backup schedule
        show_step(1)
        self.update_backup_schedule(reclass)

        # Apply 'backupninja' state on backupninja client node
        show_step(2)
        salt.enforce_state("I@backupninja:client", "backupninja")

        # Wait until backup is triggered by schedule
        show_step(3)
        helpers.wait_pass(
            lambda: ssh.check_call(
                cmd="pgrep backupninja && echo OK", node_name=backup_client),
            timeout=60 * 11,
            interval=5)

        # Wait until backup is finished
        show_step(4)
        ssh.check_call(
            cmd="while pgrep backupninja > /dev/null; do sleep 2; done",
            node_name=backup_client,
            timeout=60 * 5)

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(5)
        self.check_salt_master_backup(
            ssh, backup_server, self.BCKP_SERVER_DIR, backup_client)

        # Simulate loss/change of some reclass data
        show_step(6)
        self.delete_reclass_files(ssh, backup_client)
        hashes = self.update_reclass_files(ssh, backup_client)

        # Restore the backup
        show_step(7)
        ssh.check_call(
            "salt-call state.sls salt.master.restore,salt.minion.restore",
            node_name=backup_client,
            raise_on_err=False,
            timeout=60 * 4)

        # Verify that all pieces of lost/changed data are restored
        show_step(8)
        self.verify_restored_data(ssh, backup_client, hashes)

        # Ping minions
        show_step(9)
        salt.local('*', "test.ping", timeout=30)

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.backup_all
    def _test_backup_cfg_backupninja_rsync(
            self, underlay, config, openstack_deployed,
            salt_actions, show_step):
        """Test backup restore master node

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Check config for rsync exists
            5. Run backup command
            6. Delete salt master pki
            7. Run restore
            8. Check pki was restored
            9. Check minions work fine with master

        """
        backup = backup_restore_manager.BackupRestoreManager(
            config=config, underlay=underlay, salt_api=salt_actions)
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        backup.check_file_exists('cfg01')

        # STEP #5
        show_step(5)
        backup.create_backup('cfg01')

        # STEP #6
        show_step(6)
        backup.delete_dirs_files('cfg01')

        # STEP #7
        show_step(7)
        backup.restore_salt('cfg01')

        # STEP #8
        show_step(8)
        backup.verify_salt_master_restored('cfg01')

        # STEP #9
        show_step(9)
        backup.ping_minions('cfg01')

        LOG.info("*************** DONE **************")


class TestBackupVCP(object):
    """Test class for testing backup restore of VCP nodes"""
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.backup_all
    def test_backup_restore_glance_images(
            self, underlay, config, openstack_deployed,
            salt_actions, show_step):
        """Test backup restore glance images

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Copy the images to the backup destination
            5. Get image file uuid on fs
            6. Delete image on fs
            7. Copy the images from the backup directory to the Glance folder
            8. Verify if the restored Glance images are available
            9. Download image from glance
        """
        backup = backup_restore_manager.BackupRestoreManager(
                config=config, underlay=underlay, salt_api=salt_actions)
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)
        backup.create_cirros()
        # STEP #4
        show_step(4)
        backup.copy_glance_images_to_backup(
            path_to_backup='/srv/volumes/backup/')

        # STEP #5
        show_step(5)
        uuid = backup.get_image_uud()['stdout'][0].rstrip()

        # STEP #6
        show_step(6)
        backup.delete_image_from_fs(uuid)

        # STEP #7
        show_step(7)
        backup.copy_glance_images_from_backup(
            path_to_backup='/srv/volumes/backup/')

        # STEP #8
        show_step(8)
        backup.check_image_on_fs(uuid)

        # STEP #9
        show_step(9)
        backup.check_image_after_backup(uuid)
        LOG.info("*************** DONE **************")
