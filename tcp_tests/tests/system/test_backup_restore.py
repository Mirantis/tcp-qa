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
import itertools
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

    # Salt master backup/restore related data
    SM_DIRS = ["/srv/salt/reclass", "/etc/pki/ca", "/etc/salt/pki"]
    SM_FILE_TO_DELETE = "sm_file_to_delete.txt"
    SM_FILE_TO_UPDATE = "sm_file_to_update.txt"
    SM_FLAG_FILES = ["/srv/salt/master-restored", "/srv/salt/minion-restored"]
    SM_BACKUP_DIRS = ["etc/pki", "etc/salt", "srv/salt"]
    SM_YAML = "cluster/*/infra/config/init.yml"

    # MAAS backup/restore related data
    MAAS_DIRS = ["/var/lib/maas", "/etc/maas"]
    MAAS_FILE_TO_DELETE = "maas_file_to_delete.txt"
    MAAS_FILE_TO_UPDATE = "maas_file_to_update.txt"
    MAAS_FLAG_FILES = ["/root/maas/flags/*"]
    MAAS_BACKUP_DIRS = ["etc/maas", "var/backups/postgresql", "var/lib/maas"]
    MAAS_SERVICES = ["maas-dhcpd", "maas-proxy", "maas-rackd", "maas-regiond"]
    MAAS_YAML = "cluster/*/infra/maas.yml"

    # Jenkins pipeline data
    BACKUP_JOB_NAME = "backupninja_backup"
    BACKUP_JOB_PARAMETERS = {
        "ASK_CONFIRMATION": False
    }
    RESTORE_JOB_NAME = "backupninja_restore"
    JENKINS_START_TIMEOUT = 60
    JENKINS_BUILD_TIMEOUT = 60 * 30

    @pytest.fixture
    def cleanup_actions(self, underlay_actions, salt_actions, reclass_actions):
        """Cleanup/restore actions for backup/restore scenarios

        - If exists, remove flag files, which indicate that
        backup restore procedure has already been executed.
        - Set backup schedule to default (1.00 AM) value.

        :param underlay_actions: UnderlaySSHManager, tcp-qa SSH manager
            instance
        :param salt_actions: SaltManager, tcp-qa Salt manager instance
        :param reclass_actions: ReclassManager, tcp-qa Reclass-tools manager
        """
        sm = salt_actions.local(
            "I@salt:master", "test.ping")['return'][0].keys()[0]
        server = salt_actions.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]
        flag_files = self.SM_FLAG_FILES + self.MAAS_FLAG_FILES

        def cleanup(underlay_actions, server, sm, flag_files):
            # Delete restore flag files from Salt master, if exist
            for f in flag_files:
                underlay_actions.check_call(
                    "rm -rf {}".format(f),
                    node_name=sm,
                    raise_on_err=False)

        cleanup(underlay_actions, server, sm, flag_files)
        yield
        cleanup(underlay_actions, server, sm, flag_files)

        # Change backup schedule to default values
        for path in (self.MAAS_YAML, self.SM_YAML):
            reclass_actions.add_key(
                "parameters.backupninja.client.backup_times.hour",
                "\"'1'\"",
                path)
            reclass_actions.add_key(
                "parameters.backupninja.client.backup_times.minute",
                "\"'0'\"",
                path)

    def check_backup(self, ssh, server, path, client_name, dirs):
        """Check that data directories exist in backup on backup server

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param server: string, backup server node where backup is stored
        :param path: string, path to backupninja inventory of backups on server
        :param client_name: string, backup client node name, which indicates
            the name of backup on backup server
        :param dirs: list, list of data directories of the backup on server
        """
        for d in dirs:
            cmd = "test -d {}/{}/{}".format(path, client_name, d)
            result = ssh.check_call(
                cmd, node_name=server, raise_on_err=False)['exit_code']
            assert result == ExitCodes.EX_OK, (
                "'{}' data from {} is not in backup.".format(d, client_name))

    def delete_files(self, ssh, client, base_dirs, file_to_delete):
        """Delete files from the given location

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are deleted
        :param base_dirs: list, directories from where to delete the given file
        :param file_to_delete: string, name of the file to be deleted
        """
        for base_dir in base_dirs:
            ssh.check_call(
                "rm {}/{}".format(base_dir, file_to_delete),
                node_name=client,
                raise_on_err=False)

    def update_files(self, ssh, client, base_dirs, file_to_update):
        """Update given files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are updated
        :param base_dirs: list, directories where to update the given file
        :param file_to_update: list, name of the file to be updated
        :return: dict, key-value pairs of files and their hashes before update
        """
        hashes = {}
        for base_dir in base_dirs:
            path = "{}/{}".format(base_dir, file_to_update)
            # Calculate hash of a file
            hashes[path] = ssh.check_call(
                "sha1sum {} | awk '{{print $1}}'".format(path),
                node_name=client,
                raise_on_err=False)['stdout']
            # Update a file with a dummy string
            ssh.check_call(
                "echo '{}' >> {}".format("#" * 200, path),
                node_name=client,
                raise_on_err=False)
        return hashes

    def update_backup_schedule(self, reclass, path):
        """Update backup schedule on backupninja client

        :param reclass: ReclassManager, tcp-qa Reclass-tools manager
        :param path: str, path to YAML file to update
        """
        reclass.add_bool_key("parameters.backupninja.enabled", "True", path)
        reclass.add_key(
            "parameters.backupninja.client.backup_times.hour",
            "\"'*'\"",
            path)
        reclass.add_key(
            "parameters.backupninja.client.backup_times.minute",
            "\"'*/10'\"",
            path)

    def _precreate_test_files(self, salt, ssh, base_dirs, test_files):
        """Prepare test files for scenarios

        :param salt: SaltManager, tcp-qa Salt manager instance
        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param base_dirs: list, list of paths
        :param test_files: list, list of file names - test files to be created
        """
        sm = salt.local("I@salt:master", "test.ping")['return'][0].keys()[0]
        paths = list(itertools.product(base_dirs, list(test_files)))
        for base_dir, filename in paths:
            ssh.check_call(
                "echo 'Test file' > {}/{}".format(base_dir, filename),
                node_name=sm,
                raise_on_err=False)

    @pytest.fixture
    def maas_test_setup(self, underlay_actions, salt_actions, reclass_actions):
        """Setup for MAAS backup/restore tests

        :param underlay_actions: UnderlaySSHManager, tcp-qa SSH manager
            instance
        :param salt_actions: SaltManager, tcp-qa Salt manager instance
        :param reclass_actions: ReclassManager, tcp-qa Reclass-tools manager
        """
        # Check if 'postgresql-client-9.6' package is installed on backupninja
        # client node. Install if necessary.
        postgresql_pkg = "postgresql-client"
        postgresql_pkg_ver = "9.6"
        sm = salt_actions.local(
            "I@salt:master", "test.ping")['return'][0].keys()[0]

        result = salt_actions.local(
            sm, "pkg.info_installed", postgresql_pkg)['return'][0]
        installed_ver = result[sm][postgresql_pkg].get('version')
        if not(installed_ver and postgresql_pkg_ver in installed_ver):
            pkg = "{pkg},{pkg}-{ver}".format(
                pkg=postgresql_pkg, ver=postgresql_pkg_ver)
            salt_actions.local(sm, "pkg.install", pkg)

        # Precreate test files for MAAS backup/restore test scenarios
        self._precreate_test_files(
            salt_actions,
            underlay_actions,
            self.MAAS_DIRS,
            [self.MAAS_FILE_TO_DELETE, self.MAAS_FILE_TO_UPDATE])

        # Enable MAAS restore in reclass
        restore_class = "system.maas.region.restoredb"
        if restore_class not in reclass_actions.get_key(
                "classes", self.MAAS_YAML):
            reclass_actions.add_class(restore_class, self.MAAS_YAML)

    @pytest.fixture
    def precreate_sm_test_files(self, underlay_actions, salt_actions):
        """Create test files before executing Salt Master backup

        :param underlay_actions: UnderlaySSHManager, tcp-qa SSH manager
            instance
        :param salt_actions: SaltManager, tcp-qa Salt manager instance
        """
        self._precreate_test_files(
            salt_actions,
            underlay_actions,
            self.SM_DIRS,
            [self.SM_FILE_TO_DELETE, self.SM_FILE_TO_UPDATE])

    def verify_restored_data(
            self, ssh, client, base_dirs, deleted_file, updated_file, hashes):
        """Verify restore of deleted/updated files

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param client: string, backup client node where files are updated
        :param deleted_file: string, name of the deleted file
        :param updated_file: string, name of the updated file
        :param hashes: dict, key-value pairs of files and their hashes
            before update
        """
        for base_dir in base_dirs:
            # Verify that deleted files are restored
            path = "{}/{}".format(base_dir, deleted_file)
            result = ssh.check_call(
                "test -f {}".format(path),
                node_name=client,
                raise_on_err=False)['exit_code']
            assert result == ExitCodes.EX_OK, (
                "'{}' data is not in restored on {}.".format(path, client))

            # Verify that changed files are reverted
            path = "{}/{}".format(base_dir, updated_file)
            f_hash = ssh.check_call(
                "sha1sum {} | awk '{{print $1}}'".format(path),
                node_name=client,
                raise_on_err=False)['stdout']
            assert hashes[path] == f_hash, (
                "'{}' data is not in restored on {}.".format(path, client))

    def get_maas_svc_status(self, salt, client):
        """Get status of MAAS services

        :param salt: SaltManager, tcp-qa Salt manager instance
        :param client: string, backup client node where files are updated
        :return: dict, statuses of MAAS services
        """
        statuses = {}
        for svc in self.MAAS_SERVICES:
            statuses[svc] = salt.service_status(
                "I@maas:region", svc)[0][client]
        return statuses

    @pytest.mark.grab_versions
    @pytest.mark.salt_master_manual_backup_restore
    def test_salt_master_manual_backup_restore(
            self,
            underlay_actions,
            salt_actions,
            show_step,
            precreate_sm_test_files,
            cleanup_actions):
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

        sm = salt.local(
            "I@salt:master", "test.ping")['return'][0].keys()[0]
        server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Create backup by moving local files to the 'backupninja' server
        show_step(1)
        cmd = "backupninja -n --run /etc/backup.d/200.backup.rsync"
        ssh.check_call(cmd, node_name=sm, raise_on_err=False, timeout=60 * 4)

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(2)
        self.check_backup(
            ssh, server, self.BCKP_SERVER_DIR, sm, self.SM_BACKUP_DIRS)

        # Simulate loss/change of some reclass data
        show_step(3)
        self.delete_files(ssh, sm, self.SM_DIRS, self.SM_FILE_TO_DELETE)
        hashes = self.update_files(
            ssh, sm, self.SM_DIRS, self.SM_FILE_TO_UPDATE)

        # Restore the backup
        show_step(4)
        ssh.check_call(
            "salt-call state.sls salt.master.restore,salt.minion.restore",
            node_name=sm,
            raise_on_err=False,
            timeout=60 * 4)

        # Verify that all pieces of lost/changed data are restored
        show_step(5)
        self.verify_restored_data(
            ssh,
            sm,
            self.SM_DIRS,
            self.SM_FILE_TO_DELETE,
            self.SM_FILE_TO_UPDATE,
            hashes)

        # Ping minions
        show_step(6)
        salt.local('*', "test.ping", timeout=30)

    @pytest.mark.grab_versions
    @pytest.mark.salt_master_manual_backup_restore_pipeline
    def test_salt_master_manual_backup_restore_pipeline(
            self,
            underlay_actions,
            salt_actions,
            drivetrain_actions,
            show_step,
            precreate_sm_test_files,
            cleanup_actions):
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
        dt = drivetrain_actions

        sm = salt.local("I@salt:master", "test.ping")['return'][0].keys()[0]
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
            "'{}' job run status is {} after creating Salt master backup. "
            "Please check the build and executed stages.".format(
                self.BACKUP_JOB_NAME, status)
        )

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(2)
        self.check_backup(
            ssh, server, self.BCKP_SERVER_DIR, sm, self.SM_BACKUP_DIRS)

        # Simulate loss/change of some reclass data
        show_step(3)
        self.delete_files(ssh, sm, self.SM_DIRS, self.SM_FILE_TO_DELETE)
        hashes = self.update_files(
            ssh, sm, self.SM_DIRS, self.SM_FILE_TO_UPDATE)

        # Restore the backup
        show_step(4)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.RESTORE_JOB_NAME,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{}' job run status is {} after restoring from Salt master "
            "backup. Please check the build and executed stages.".format(
                self.RESTORE_JOB_NAME, status)
        )

        # Verify that all pieces of lost/changed data are restored
        show_step(5)
        self.verify_restored_data(
            ssh,
            sm,
            self.SM_DIRS,
            self.SM_FILE_TO_DELETE,
            self.SM_FILE_TO_UPDATE,
            hashes)

        # Ping minions
        show_step(6)
        salt.local('*', "test.ping", timeout=30)

    @pytest.mark.grab_versions
    @pytest.mark.salt_master_scheduled_backup_restore
    def test_salt_master_scheduled_backup_restore(
            self,
            underlay_actions,
            salt_actions,
            reclass_actions,
            show_step,
            precreate_sm_test_files,
            cleanup_actions):
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

        sm = salt.local("I@salt:master", "test.ping")['return'][0].keys()[0]
        server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Re-configure backup schedule
        show_step(1)
        self.update_backup_schedule(reclass, self.SM_YAML)

        # Apply 'backupninja' state on backupninja client node
        show_step(2)
        salt.enforce_state("I@backupninja:client", "backupninja")

        # Wait until backup is triggered by schedule
        show_step(3)
        helpers.wait_pass(
            lambda: ssh.check_call(
                cmd="pgrep backupninja && echo OK", node_name=sm),
            timeout=60 * 11,
            interval=5)

        # Wait until backup is finished
        show_step(4)
        ssh.check_call(
            cmd="while pgrep backupninja > /dev/null; do sleep 2; done",
            node_name=sm,
            timeout=60 * 5)

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(5)
        self.check_backup(
            ssh, server, self.BCKP_SERVER_DIR, sm, self.SM_BACKUP_DIRS)

        # Simulate loss/change of some reclass data
        show_step(6)
        self.delete_files(ssh, sm, self.SM_DIRS, self.SM_FILE_TO_DELETE)
        hashes = self.update_files(
            ssh, sm, self.SM_DIRS, self.SM_FILE_TO_UPDATE)

        # Restore the backup
        show_step(7)
        ssh.check_call(
            "salt-call state.sls salt.master.restore,salt.minion.restore",
            node_name=sm,
            raise_on_err=False,
            timeout=60 * 4)

        # Verify that all pieces of lost/changed data are restored
        show_step(8)
        self.verify_restored_data(
            ssh,
            sm,
            self.SM_DIRS,
            self.SM_FILE_TO_DELETE,
            self.SM_FILE_TO_UPDATE,
            hashes)

        # Ping minions
        show_step(9)
        salt.local('*', "test.ping", timeout=30)

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.maas_backup_restore_manual
    def test_maas_backup_restore_manual(
            self,
            salt_actions,
            underlay_actions,
            show_step,
            maas_test_setup,
            cleanup_actions):
        """Test backup and restore of MAAS PostgreSQL DB

        Scenario:
        1. Make backup of file permissions for MAAS
        2. Compress all MAAS PostgreSQL databases and store locally
        3. Move local backup files to backupninja server
        4. Verify that MAAS backup is rsynced to backupninja server
        5. Delete/change some MAAS data
        6. Restore the backup
        7. Verify that MAAS data backup is restored
        8. Verify MAAS services after restore

        Duration: ~
        """
        salt = salt_actions
        ssh = underlay_actions

        sm = salt.local("I@salt:master", "test.ping")['return'][0].keys()[0]
        server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Make backup of file permissions for MAAS
        show_step(1)
        perm_file = "/var/lib/maas/file_permissions.txt"
        ssh.check_call(
            "which getfacl && getfacl -pR /var/lib/maas/ > {}".format(
                perm_file),
            node_name=sm,
            raise_on_err=False)['stdout_str']
        result = ssh.check_call(
            "test -f {}".format(perm_file),
            node_name=sm,
            raise_on_err=False)['exit_code']
        assert result == ExitCodes.EX_OK, (
            "Local backup of MAAS files permissions is not created")

        # Make local backup of MAAS PostgreSQL DBs
        show_step(2)
        cmd = "backupninja -n --run /etc/backup.d/102.pgsql"
        ssh.check_call(cmd, node_name=sm, raise_on_err=False, timeout=60 * 5)
        result = ssh.check_call(
            "test -f {}".format("/var/backups/postgresql/maasdb.pg_dump.gz"),
            node_name=sm,
            raise_on_err=False)['exit_code']
        assert result == ExitCodes.EX_OK, (
            "Local backup of MAAS PostgreSQL DBs is not created")

        # Rsync local backup to backupninja server
        show_step(3)
        cmd = "backupninja -n --run /etc/backup.d/200.backup.rsync"
        ssh.check_call(cmd, node_name=sm, raise_on_err=False, timeout=60 * 5)

        # Verify all pieces of backup data are rsynced to backupninja server
        show_step(4)
        self.check_backup(
            ssh, server, self.BCKP_SERVER_DIR, sm, self.MAAS_BACKUP_DIRS)

        # Simulate loss/change of some MAAS data
        show_step(5)
        self.delete_files(ssh, sm, self.MAAS_DIRS, self.MAAS_FILE_TO_DELETE)
        hashes = self.update_files(
            ssh, sm, self.MAAS_DIRS, self.MAAS_FILE_TO_UPDATE)

        # Restore the backup
        show_step(6)
        salt.enforce_state("I@maas:region", "maas.region")

        # Verify that all pieces of lost/changed data are restored
        show_step(7)
        self.verify_restored_data(
            ssh,
            sm,
            self.MAAS_DIRS,
            self.MAAS_FILE_TO_DELETE,
            self.MAAS_FILE_TO_UPDATE,
            hashes)

        # Verify that MAAS services are up and running after restore
        show_step(8)
        statuses = self.get_maas_svc_status(salt, sm)
        assert all(statuses.values()), (
            "Not all MAAS services are active after restore. Please check the "
            "affected services (marked as 'False' below):\n{}".format(statuses)
        )

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.maas_manual_backup_restore_pipeline
    def test_maas_manual_backup_restore_pipeline(
            self,
            underlay_actions,
            salt_actions,
            drivetrain_actions,
            show_step,
            maas_test_setup,
            cleanup_actions):
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

        sm = salt.local("I@salt:master", "test.ping")['return'][0].keys()[0]
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
        self.check_backup(
            ssh, server, self.BCKP_SERVER_DIR, sm, self.MAAS_BACKUP_DIRS)

        # Simulate loss/change of some MAAS data
        show_step(3)
        self.delete_files(ssh, sm, self.MAAS_DIRS, self.MAAS_FILE_TO_DELETE)
        hashes = self.update_files(
            ssh, sm, self.MAAS_DIRS, self.MAAS_FILE_TO_UPDATE)

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
        self.verify_restored_data(
            ssh,
            sm,
            self.MAAS_DIRS,
            self.MAAS_FILE_TO_DELETE,
            self.MAAS_FILE_TO_UPDATE,
            hashes)

        # Verify that MAAS services are up and running after restore
        show_step(6)
        statuses = self.get_maas_svc_status(salt, sm)
        assert all(statuses.values()), (
            "Not all MAAS services are active after restore. Please check the "
            "affected services (marked as 'False' below):\n{}".format(statuses)
        )

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.maas_scheduled_backup_restore
    def test_maas_scheduled_backup_restore(
            self,
            underlay_actions,
            salt_actions,
            reclass_actions,
            show_step,
            cleanup_actions):
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

        sm = salt.local("I@salt:master", "test.ping")['return'][0].keys()[0]
        server = salt.local(
            "I@backupninja:server", "test.ping")['return'][0].keys()[0]

        # Re-configure backup schedule
        show_step(1)
        self.update_backup_schedule(reclass, self.MAAS_YAML)

        # Apply 'backupninja' state on backupninja client node
        show_step(2)
        salt.enforce_state("I@backupninja:client", "backupninja")

        # Wait until backup is triggered by schedule
        show_step(3)
        helpers.wait_pass(
            lambda: ssh.check_call(
                cmd="pgrep backupninja && echo OK", node_name=sm),
            timeout=60 * 11,
            interval=5)

        # Wait until backup is finished
        show_step(4)
        ssh.check_call(
            cmd="while pgrep backupninja > /dev/null; do sleep 2; done",
            node_name=sm,
            timeout=60 * 5)

        # Verify that backup is created and all pieces of data are rsynced
        # to backupninja server
        show_step(5)
        self.check_backup(
            ssh, server, self.BCKP_SERVER_DIR, sm, self.MAAS_BACKUP_DIRS)

        # Simulate loss/change of some MAAS data
        show_step(6)
        self.delete_files(ssh, sm, self.MAAS_DIRS, self.MAAS_FILE_TO_DELETE)
        hashes = self.update_files(
            ssh, sm, self.MAAS_DIRS, self.MAAS_FILE_TO_UPDATE)

        # Restore the backup
        show_step(7)
        salt.enforce_state("I@maas:region", "maas.region")

        # Verify that all pieces of lost/changed data are restored
        show_step(8)
        self.verify_restored_data(
            ssh,
            sm,
            self.MAAS_DIRS,
            self.MAAS_FILE_TO_DELETE,
            self.MAAS_FILE_TO_UPDATE,
            hashes)

        # Verify that MAAS services are up and running after restore
        show_step(9)
        statuses = self.get_maas_svc_status(salt, sm)
        assert all(statuses.values()), (
            "Not all MAAS services are active after restore. Please check the "
            "affected services (marked as 'False' below):\n{}".format(statuses)
        )

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
