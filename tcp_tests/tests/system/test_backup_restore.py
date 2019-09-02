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

LOG = logger.logger


class TestBackupRestoreMaster(object):
    """Test class for testing backup restore of master node"""

    ENV_NAME = settings.ENV_NAME

    BCKP_SERVER_DIR = "/srv/volumes/backup/backupninja"
    MAAS_DIR = "/var/lib/maas/"
    FILES_TO_DELETE = [  
    ]
    FILES_TO_UPDATE = [
    ]

    BACKUP_JOB_NAME = 'backupninja_backup'
    BACKUP_JOB_PARAMETERS = {
        "ASK_CONFIRMATION": False
    }
    RESTORE_JOB_NAME = 'backupninja_restore'
    JENKINS_START_TIMEOUT = 60
    JENKINS_BUILD_TIMEOUT = 60 * 30

    def check_maas_backup(self, ssh, server, path, client):
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
                "'{}' MAAS data is not in backup.".format(subdir))

    def delete_maas_files(self, ssh, client):
        """Delete several MAAS files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are deleted
        """
        files_to_delete = " ".join(self.FILES_TO_DELETE)
        ssh.check_call(
            "cd {}; rm {}".format(self.MAAS_DIR, files_to_delete),
            node_name=client,
            raise_on_err=False)

    def update_maas_files(self, ssh, client):
        """Update several MAAS files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are updated
        :return: dict, key-value pairs of files and their hashes before update
        """
        hashes = {}
        for f in self.FILES_TO_UPDATE:
            path = "{}/{}".format(self.MAAS_DIR, f)
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

    def verify_restored_data(self, ssh, client, hashes):
        """Verify restore of deleted and updated MAAS files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are updated
        :param hashes: dict, key-value pairs of files and their hashes
            before update
        """
        # Verify that deleted files are restored
        for f in self.FILES_TO_DELETE:
            path = "{}/{}".format(self.MAAS_DIR, f)
            result = ssh.check_call(
                "test -f {}".format(path),
                node_name=client,
                raise_on_err=False)['exit_code']
            assert result == ExitCodes.EX_OK, (
                "'{}' MAAS data is not in restored.".format(path))
        # Verify that changed files are restored
        for f in self.FILES_TO_UPDATE:
            path = "{}/{}".format(self.MAAS_DIR, f)
            f_hash = ssh.check_call(
                "sha1sum {} | awk '{{print $1}}'".format(path),
                node_name=client,
                raise_on_err=False)['stdout']
            assert hashes[f] == f_hash, (
                "'{}' MAAS data is not in restored.".format(path))

    #@pytest.mark.grab_versions
    #@pytest.mark.fail_snapshot
    @pytest.mark.maas_backup_restore_manual
    def test_maas_backup_restore_manual(
            self,
            salt_actions,
            reclass_actions,
            underlay_actions,
            show_step,
            delete_backup):
        """Test backup and restore of MAAS PostgreSQL DB

        Scenario:
        1. Enforce 'postgresql-client' package on backupninja client node
        2. Make backup of file permissions for MAAS
        3. Compress all MAAS PostgreSQL databases and store locally
        4. Move local backup files to backupninja server
        5. Verify that MAAS backup is rsynced to backupninja server
        6. Delete/change some MAAS data
        7. Restore the backup
        8. Verify that MAAS data backup is restored
        9. Verify MAAS services after restore

        Duration: ~
        """
        salt = salt_actions
        reclass = reclass_actions
        ssh = underlay_actions

        postgresql_pkg = "postgresql-client"
        postgresql_pkg_ver = "9.6"
        client = salt_actions.local(
            "I@backupninja:client", "test.ping")['return'][0].keys()[0]
        server = salt_actions.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Check if 'postgresql-client-9.6' package is installed on backupninja
        # client node. Install oif necessary.
        show_step(1)
        result = salt.pkg_info_installed(client, postgresql_pkg)[0]
        installed_ver = result[client][postgresql_pkg].get('version')
        if not(installed_ver and postgresql_pkg_ver in installed_ver):
            salt.pkg_install(
                client,
                "{0},{0}-{1}".format(postgresql_pkg, postgresql_pkg_ver))

        # Make backup of file permissions for MAAS
        show_step(2)
        perm_file = "/var/lib/maas/file_permissions.txt"
        ssh.check_call(
            "which getfacl && getfacl -pR /var/lib/maas/ > {}".format(
                perm_file),
            node_name=client,
            raise_on_err=False)['stdout_str']
        result = ssh.check_call(
            "test -f {}".format(perm_file),
            node_name=client,
            raise_on_err=False)['exit_code']
        assert result == ExitCodes.EX_OK, (
            "Local backup of MAAS files permissions is not created")

        # Make local backup of MAAS PostgreSQL DBs
        show_step(3)
        cmd = "backupninja -n --run /etc/backup.d/102.pgsql"
        ssh.check_call(
            cmd, node_name=client, raise_on_err=False, timeout=60 * 5)
        result = ssh.check_call(
            "test -d {}".format("/var/backups/postgresql"),
            node_name=client,
            raise_on_err=False)['exit_code']
        assert result == ExitCodes.EX_OK, (
            "Local backup of MAAS PostgreSQL DBs is not created")

        # Rsync local backup to backupninja server
        show_step(4)
        cmd = "backupninja -n --run /etc/backup.d/200.backup.rsync"
        ssh.check_call(
            cmd, node_name=client, raise_on_err=False, timeout=60 * 5)

        # Verify all pieces of backup data are rsynced to backupninja server
        show_step(5)
        self.check_maas_backup(ssh, server, self.BCKP_SERVER_DIR, client)

        # Simulate loss/change of some MAAS data
        show_step(6)
        self.delete_maas_files(ssh, client)
        hashes = self.update_maas_files(ssh, client)

        # Restore the backup
        show_step(7)
        salt.enforce_state("I@maas:region", "maas.region")

        # Verify that all pieces of lost/changed data are restored
        show_step(8)
        self.verify_restored_data(ssh, client, hashes)

        # Verify that MAAS services are up and running after restore
        show_step(9)

    #@pytest.mark.grab_versions
    @pytest.mark.maas_manual_backup_restore_pipeline
    def test_maas_manual_backup_restore_pipeline(
            self,
            underlay_actions,
            salt_actions,
            drivetrain_actions,
            show_step,
            delete_backup):
        """Test manual backup restore of MAAS data using DT pipeline

        Scenario:
            1. Execute 'backupninja_backup' pipeline to backup MAAS data
            2. Verify that MAAS backup is created on backupninja server node
            3. Delete/change some MAAS data
            4. Restore the backup
            5. Verify that MAAS data backup is restored
            6. Verify MAAS services after restore

        Duration: ~ 3 min
        """
        salt = salt_actions
        ssh = underlay_actions
        dt = drivetrain_actions

        client = salt.local(
            "I@backupninja:client", "test.ping")['return'][0].keys()[0]
        server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Execute 'backupninja_backup' pipeline to create a backup
        show_step(1)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.BACKUP_JOB_NAME,
            job_parameters=self.BACKUP_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{}' job run status is {} after creating MAAS data backup. "
            "Please check the build and executed stages.".format(
                self.BACKUP_JOB_NAME, status)
        )

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(2)
        self.check_maas_backup(ssh, server, self.BCKP_SERVER_DIR, client)

        # Simulate loss/change of some MAAS data
        show_step(3)
        self.delete_maas_files(ssh, client)
        hashes = self.update_maas_files(ssh, client)

        # Restore the backup
        show_step(4)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.RESTORE_JOB_NAME,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{}' job run status is {} after restoring from MAAS "
            "backup. Please check the build and executed stages.".format(
                self.RESTORE_JOB_NAME, status)
        )

        # Verify that all pieces of lost/changed data are restored
        show_step(5)
        self.verify_restored_data(ssh, client, hashes)

        # Verify that MAAS services are up and running after restore
        show_step(6)

    @pytest.mark.maas_scheduled_backup_restore
    def test_maas_scheduled_backup_restore(
            self,
            underlay_actions,
            salt_actions,
            reclass_actions,
            show_step,
            delete_backup):
        """Test scheduled backup restore of MAAS data

        Scenario:
            1. Update MAAS backup schedule to run every 5 minutes
            2. Apply 'backupninja' state on the backupninja client node
            3. Wait until backup creation is triggered by schedule
            4. Wait until backup creation is finished
            5. Verify that MAAS backup is created on backupninja server node
            6. Delete/change some MAAS data
            7. Restore the backup
            8. Verify that MAAS data backup is restored
            9. Verify MAAS services after restore

        Duration: ~ 3 min
        """
        salt = salt_actions
        ssh = underlay_actions
        reclass = reclass_actions

        client = salt.local(
            "I@backupninja:client", "test.ping")['return'][0].keys()[0]
        server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

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
                cmd="pgrep backupninja && echo OK", node_name=client),
            timeout=60 * 11,
            interval=5)

        # Wait until backup is finished
        show_step(4)
        ssh.check_call(
            cmd="while pgrep backupninja > /dev/null; do sleep 2; done",
            node_name=client,
            timeout=60 * 5)

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(5)
        self.check_maas_backup(ssh, server, self.BCKP_SERVER_DIR, client)

        # Simulate loss/change of some MAAS data
        show_step(6)
        self.delete_maas_files(ssh, client)
        hashes = self.update_maas_files(ssh, client)

        # Restore the backup
        show_step(7)
        salt.enforce_state("I@maas:region", "maas.region")

        # Verify that all pieces of lost/changed data are restored
        show_step(8)
        self.verify_restored_data(ssh, client, hashes)

        # Verify that MAAS services are up and running after restore
        show_step(9)

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.backup_all
    def test_backup_cfg_backupninja_rsync(
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
