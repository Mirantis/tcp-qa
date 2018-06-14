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
        """Test add policy for Nova service

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
