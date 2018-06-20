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
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin


LOG = logger.logger


class BackupRestoreManager(ExecuteCommandsMixin):
    """Helper manager for execution backup restore"""

    def __init__(self, config, underlay, salt_api):
        self.__config = config
        self.underlay = underlay
        self.__salt_api = salt_api
        super(BackupRestoreManager, self).__init__(config, underlay)

    @property
    def salt_api(self):
        return self.__salt_api

    def get_node_name(self, tgt):
        res = [node_name for node_name in
               self.underlay.node_names() if tgt in node_name]
        assert len(res) > 0, 'Can not find node name by tgt {}'.format(tgt)
        return res[0]

    def create_backup(self, tgt, backup_cmd=None):
        if not backup_cmd:
            backup_cmd = 'backupninja -n --run /etc/backup.d/200.backup.rsync'
        step = {'cmd': backup_cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Running backup command')

    def check_file_exists(self, tgt, file_path=None):
        if not file_path:
            file_path = '/etc/backup.d/200.backup.rsync'
        cmd = 'test -f {}'.format(file_path)
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Check file {} exists'.format(file_path))

    def delete_dirs_files(self, tgt, file_path='/etc/pki/ca/salt_master_ca/'):
        cmd = 'rm -rf {}'.format(file_path)
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Delete {}'.format(file_path))

    def restore_salt(self, tgt):
        cmd = 'salt-call state.sls salt.master.restore,salt.minion.restore'
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Restore salt master')

    def ping_minions(self, tgt):
        cmd = 'salt "*" test.ping'
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Ping minions')

    def verify_salt_master_restored(self, tgt):
        cmd = "salt -t2 '*' saltutil.refresh_pillar"
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step,
                             'Verify that the Salt Master node is restored')
        step = {'cmd': 'ls -la /etc/pki/ca/salt_master_ca/',
                'node_name': self.get_node_name(tgt)}
        self.execute_command(step,
                             'Check pki files exists')

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

    def create_mysql_xtrabackup(self, tgt, backup_cmd=None):
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
        # TODO finds the way updated wresp
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

    # #################Backup_Restore_Glance###################

    def copy_glance_images_to_backup(self, path_to_backup,
                                     tgt="ctl03"):
        cmd = 'cp -a /var/lib/glance/images/. {}'.format(path_to_backup)
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        return self.execute_command(step, 'Copy glance images to backup')

    def get_image_uud(self, tgt='ctl03'):
        cmd = (". /root/keystonercv3; "
               "openstack image list -c ID|  awk 'NR==4'| cut -d '|' -f 2")
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        res = self.execute_command(step, 'Get uuid of image on fs',
                                   return_res=True)
        return res

    def delete_image_from_fs(self, uuid, tgt="ctl03"):
        cmd = ('cd /var/lib/glance/images/; rm {}'.format(uuid))
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Delete image before restore')

    def copy_glance_images_from_backup(self, path_to_backup,
                                       tgt="ctl03"):
        cmd = 'cp -a {}/. /var/lib/glance/images/'.format(path_to_backup)
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        return self.execute_command(step, 'Copy to glance')

    def check_image_on_fs(self, uuid, tgt="ctl03"):
        cmd = ('ls /var/lib/glance/images/ grep {}'.format(uuid))
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Check image exists after restore')

    def check_image_after_backup(self, uuid, tgt="ctl03"):
        cmd = '. /root/keystonercv3; openstack image save {}'.format(uuid)
        step = {'cmd': cmd, 'node_name': self.get_node_name(tgt)}
        self.execute_command(step, 'Save image after backup')
