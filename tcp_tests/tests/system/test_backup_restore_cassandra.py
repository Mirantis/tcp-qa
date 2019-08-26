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

LOG = logger.logger


class TestBackupRestoreCassandra(object):
    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_backup_restore_cassandra(self, salt_actions, reclass_actions,
                                      show_step, _):
        """ Backup and restore Cassandra Database

        Scenario:
            1. Enable Cassandra backup. Configure the cassandra server role
            2. Enable Cassandra backup. Configure the cassandra client role
            3. Refresh pillars on all the nodes
            4. Apply the salt.minion state
            5. Refresh grains and mine for the cassandra client node
            6. Add a Cassandra user
            7. Apply required state on the cassandra client nodes
            8. Apply required state on the cassandra server nodes

            2. Create an instant backup
            3. Restore from the backup
        """
        salt = salt_actions
        reclass = reclass_actions
        show_step(1)
        reclass.add_bool_key("parameters._param.cassandra.server.enabled",
                             "True",
                             "cluster/*/infra/backup/server.yml")
        reclass.add_key("parameters._param.cassandra.server.hours_before_full",
                        "24",
                        "cluster/*/infra/backup/server.yml")
        reclass.add_key("parameters._param.cassandra.server.full_backups_to_keep",
                        "5",
                        "cluster/*/infra/backup/server.yml")
        reclass.add_bool_key("parameters._param.cassandra.server.cron",
                             "True",
                             "cluster/*/infra/backup/server.yml")
        # there is another backup_dir, but not under server
        reclass.add_key("parameters._param.cassandra.server.backup_dir",
                        "/srv/volumes/backup/cassandra",
                        "cluster/*/infra/backup/server.yml")
        show_step(2)
        reclass.add_bool_key("parameters._param.cassandra.backup.cron",
                             "True",
                             "cluster/*/opencontrail/control_init.yml")
        # verify cassandra_remote_backup_server?!
        show_step(3)
        salt.run_state("*", "saltutil.refresh_pillar")
        LOG.info(_)
        show_step(4)
        salt.run_state("I@cassandra:backup:client or I@cassandra:backup:server", "state.sls salt.minion")
        LOG.info(_)
        show_step(5)
        salt.run_state("I@cassandra:backup:client", "saltutil.sync_grains")
        LOG.info(_)
        salt.run_state("I@cassandra:backup:client", "saltutil.mine.flush")
        LOG.info(_)
        salt.run_state("I@cassandra:backup:client", "saltutil.mine.update")
        LOG.info(_)
        show_step(6)
        salt.run_state("I@cassandra:backup:server", "state.apply linux.system")
        LOG.info(_)
        show_step(7)
        salt.run_state("I@cassandra:backup:client", "state.sls openssh.client,cassandra.backup")
        LOG.info(_)
        show_step(8)
        salt.run_state("I@cassandra:backup:server", "state.sls cassandra")
        LOG.info(_)
