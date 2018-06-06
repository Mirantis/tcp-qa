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

import os
import json

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests import settings


LOG = logger.logger

class BackupRestoreManager(object):
    """Helper manager for execution backup restore"""

    backup_cmd = 'backupninja -n --run /etc/backup.d/200.backup.rsync'

    def __init__(self, underlay, salt_api, backup_cmd=None):
        self.underlay = underlay
        self.__salt_api = salt_api
        self.backup_cmd = backup_cmd or self.backup_cmd

    @property
    def salt_api(self):
        return self.__salt_api

    def create_backup(self, tgt, backup_cmd=backup_cmd):
        return self.salt_api.enforce_state(tgt, 'cmd.run', backup_cmd)

    def restore_salt_master(self, tgt):
        return self.salt_api.local(tgt, 'salt.master.restore')

    def restore_salt_minion(self, tgt):
        return self.salt_api.local(tgt, 'salt.minion.restore')

    def create_mysql_backup_backupninja(self, tgt, ):
        rets = []
        res = self.salt_api.enforce_state(
            tgt, 'cmd.run',
            'backupninja -n --run /etc/backup.d/101.mysql')
        rets.append(res)
        res_rsync = self.salt_api.enforce_state(tgt, 'cmd.run')
        rets.append(res_rsync)
        return rets

    def restore_mysql_backupninja(self, tgt):
        # Running this state restores the databases and creates a file
        # for every restored database in /root/mysql/flags.
        return self.salt_api.local(tgt, 'mysql.client')

    def create_mysql_xtrabackup(self, tgt, backup_cmd=backup_cmd):
        # Should be run on mysql master node
        return self.salt_api.enforce_state(
            tgt, 'cmd.run', '/usr/local/bin/innobackupex-runner.sh')

    def check_mysql_xtrabackup_rsynced(self, tgt='I@xtrabackup:server'):
        return self.salt_api.enforce_state(
            tgt, 'cmd.run', 'ls /var/backups/mysql/xtrabackup/full')

    def stop_mysql_slave(self, tgt='I@galera:slave'):
        return self.salt_api.enforce_state(tgt, 'service.stop mysql')

    def remove_mysql_logs(self, tgt='I@galera:slave'):
        return self.salt_api.enforce_state(
            tgt, 'cmd.run', 'rm /var/lib/mysql/ib_logfile*')

    def stop_mysql_master(self, tgt='I@galera:master'):
        return self.salt_api.enforce_state(tgt, 'service.stop mysql')

    def disconnect_wresp_master(self, tgt='I@galera:master'):
        # TODO fins the way updated wresp
        return self.salt_api.enforce_state(
            tgt, 'cmd.run', 'wsrep_cluster_address=gcomm://')

    def move_dbs_files_to_new_location(self, tgt='I@galera:master'):
        cmds = ['mkdir -p /root/mysql/mysql.bak/',
                'mv /var/lib/mysql/* /root/mysql/mysql.bak',
                'rm /var/lib/mysql/.galera_bootstrap']
        rest = []
        for cmd in cmds:
            res = self.salt_api.enforce_state(tgt, 'cmd.run', cmd)
            rest.append(res)
        return rest

    def check_dbs_files_removed(self, tgt='I@galera:master'):
        cmds = ['ls /var/lib/mysql/',
                'ls -ld /var/lib/mysql/.?*']
        rest = []
        for cmd in cmds:
            res = self.salt_api.enforce_state(tgt, 'cmd.run', cmd)
            rest.append(res)
        return rest

    # run xtrabackup state on node where bacakup
    def run_xtrabackup(self, tgt):
        return self.salt_api.local(tgt, 'xtrabackup')

    def start_mysql(self):
        tgts = ['I@galera:master', 'I@galera:slave']
        ret = []
        for tgt in tgts:
            res = self.salt_api.enforce_state(tgt, 'service.start mysql')
            ret.append(res)
        return ret

    def check_galera_cluster(self, tgt='I@galera:master'):
        return self.salt_api.enforce_state(
            tgt, 'mysql.status | grep -A1 wsrep_cluster_size')


    ##################Backup_Restore_Glance###################

    def copy_glance_images_to_backup(self, path_to_backup,
                                     tgt="I@glance:server and *01*"):
        cmd = 'cp -a /var/lib/glance/images/. {}'.format(path_to_backup)
        return self.salt_api.enforce_state(
            tgt, 'cmd.run', cmd)

    def copy_glance_images_from_backup(self, path_to_backup,
                                     tgt="I@glance:server and *01*"):
        cmd = 'cp -a {}/. /var/lib/glance/images/'.format(path_to_backup)
        return self.salt_api.enforce_state(
            tgt, 'cmd.run', cmd)

    def check_images_after_backup(self, tgt="I@keystone:client"):
        # TODO If the context of the Glance images files is lost, run the following commands:
        # salt -C 'I@glance:server' cmd.run "chown glance:glance <IMAGE_FILE_NAME>"
        # salt -C 'I@glance:server' cmd.run "chmod 640 <IMAGE_FILE_NAME>"
        cmd = '. /root/keystonercv3; openstack image list'
        return self.salt_api.enforce_state(tgt, 'cmd.run', cmd)

    ##################Backup_Restore_cinder_volumes_and_snapshots#############





    # TODO Verify that a complete backup was created on the MySQL Galera Database Master node
    # ls /var/backups/mysql/xtrabackup/full



    #TODO(tleontovich): add method to check needed configs
    #TODO (tleontovich): check pillars
    #TODO (tleontovich): check  backup is created, and restore restores

