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

from tcp_tests import logger
from tcp_tests.managers import backup_restore_manager

LOG = logger.logger


class TestBackupRestoreMaster(object):
    """Test class for testing backup restore of master node"""

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
