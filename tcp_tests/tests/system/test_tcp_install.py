#    Copyright 2016 Mirantis, Inc.
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
import copy

import pytest

from tcp_tests import settings
from tcp_tests.helpers import ext
from tcp_tests import logger

LOG = logger.logger


@pytest.mark.deploy
class TestTCPInstaller(object):
    """Test class for testing TCP deployment"""

    salt_cmd = 'salt -l debug '  # For debug output
    salt_call_cmd = 'salt-call -l debug '  # For debug output
    #salt_cmd = 'salt --state-verbose=False '  # For reduced output
    #salt_call_cmd = 'salt-call --state-verbose=False '  # For reduced output


    @pytest.mark.steps({
        '1': {
            'cmd': salt_cmd + "'cfg01*' state.sls linux",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '2': {
            'cmd': salt_cmd + "'cfg01*' state.sls openssh",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '3': {
            'cmd': "echo '    StrictHostKeyChecking no' >> /root/.ssh/config",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 1, 'delay': 1},
        },
        '4': {
            'cmd': salt_cmd + "'cfg01*' state.sls salt",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '5': {
            'cmd': salt_cmd + "'cfg01*' state.sls reclass.storage",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '6': {
            'cmd': salt_cmd + "'*' saltutil.refresh_pillar",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '7': {
            'cmd': salt_cmd + "'ctl*' state.sls ntp",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '8': {
            'cmd': salt_cmd + "'ctl*' state.sls linux,salt.minion,openssh",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '9': {
            'cmd': salt_cmd + "'ctl01*' state.sls keepalived",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '10': {
            'cmd': salt_cmd + "'ctl01*' cmd.run 'ip a'",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '11': {
            'cmd': salt_cmd + "'ctl0[23].*' state.sls keepalived",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '12': {
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.server.service",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '13': {
            'cmd': salt_call_cmd + "state.sls glusterfs.server.setup",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '14': {
            'cmd': "gluster peer status",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '15': {
            'cmd': "gluster volume status",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '16': {
            'cmd': salt_cmd + "'ctl*' state.sls rabbitmq",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '17': {
            'cmd': salt_call_cmd + "state.sls galera",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '18': {
            'cmd': salt_cmd + "'ctl0[23]*' state.sls galera",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '19': {
            'cmd': salt_cmd + "'ctl01*'  mysql.status | grep -A1 'wsrep_incoming_addresses:'",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '20': {
            'cmd': salt_cmd + "'ctl*' state.sls haproxy",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '21': {
            'cmd': salt_cmd + "'ctl*' cmd.run 'netstat -tulnp | grep 3306'",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '22': {
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '23': {
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl02.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '24': {
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl03.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '25': {
            'cmd': "source ~/keystonerc; keystone user-list",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '26': {
            'cmd': "source ~/keystonerc; keystone tenant-list",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '27': {
            'cmd': "source ~/keystonerc; keystone endpoint-list",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '28': {
            'cmd': salt_cmd + "'ctl*' state.sls glance",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '29': {
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.client",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '30': {
            'cmd': salt_cmd + "'ctl*' cmd.run 'df -h'",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '31': {
            'cmd': salt_call_cmd + "state.sls keystone",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '32': {
            'cmd': ("source ~/keystonerc;"
                    "wget http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-i386-disk.img;"
                    "glance image-create --name 'cirros-0.3.4'"
                    "  --disk-format qcow2 --container-format bare"
                    "  --progress --file /root/cirros-0.3.4-i386-disk.img;"
                    "glance image-list;"),
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '33': {
            'cmd': salt_cmd + "'ctl*' cmd.run 'ls -al /var/lib/keystone/fernet-keys' ",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '34': {
            'cmd': salt_cmd + "'ctl*' cinder",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '35': {
            'cmd': salt_cmd + "'ctl*' nova",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '36': {
            'cmd': "source ~/keystonerc; cinder list",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '37': {
            'cmd': "source ~/keystonerc; nova-manage service list",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '38': {
            'cmd': "source ~/keystonerc; nova list",
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '39': {
            'cmd': salt_cmd + "'ctl*' state.sls neutron",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '40': {
            'cmd': ("source ~/keystonerc;"
                    "neutron net-create --router:external=true  --shared external;"
                    "neutron subnet-create external 10.177.0.0/24;"
                    "neutron floatingip-create;"),
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '41': {
            'cmd': salt_cmd + "'ctl*' state.sls opencontrail.database",
            'node_name': 'cfg01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },
        '42': {
            'cmd': ("nodetool status;"
                    "nodetool compactionstats;"
                    "nodetool describecluster;"),
            'node_name': 'ctl01.mk20-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
        },

    })
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    # @pytest.mark.snapshot_needed
    # @pytest.mark.fail_snapshot
    def test_tcp_install_default(self, underlay, tcp_actions, steps, show_step):
        """Test for deploying an tcp environment and check it

        Scenario:
            1. Run 'linux' formula on cfg01
            2. Run 'openssh' formula on cfg01
            3. *Workaround* of the bug https://mirantis.jira.com/browse/PROD-7962
            4. Run 'salt' formula on cfg01
            5. Generate inventory for all the nodes to the /srv/salt/reclass/nodes/_generated
            6. Refresh pillars on all minions
            7. Configure ntp on controllers
            8. Configure linux, openssh and salt.minion on controllers
            9. Install keepalived on primary controller
            10. Show VIP on primary controller
            11. Install keepalived on other controllers
            12. Install glusterfs on all controllers
            13. Setup glusterfs on primary controller
            14. Show glusterfs peer status
            15. Show glusterfs volume status
            16. Install RabbitMQ on all controllers
            17. Install Galera on primary controller
            18. Install Galera on other controllers
            19. Check Galera addresses
            20. Install haproxy on all controllers
            21. Check haproxy on all controllers with Galera port
            22. Install memcached and keystone on ctl01
            23. Install memcached and keystone on ctl02
            24. Install memcached and keystone on ctl03
            25. Check keystone user-list
            26. Check keystone tenant-list
            27. Check keystone endpoint-list
            28. Install glance on controllers
            29. Install glusterfs on controllers
            30. Check that glusterfs was added on controllers
            31. *Workaround* Re-run keystone formula on ctl01 to create fernet keys
            32. Check glance on ctl01
            33. Check keystone fernet keys on controllers
            34. Install cinder on controllers
            35. Install nova on controllers
            36. Check cinder status
            37. Check nova services status
            38. Check nova status
            39. Install neutron on controllers
            40. Create a neutron subnet
            41. Install contrail database on controllers
            42. Check cassandra status on ctl01


        """
        for step in sorted(steps):
            LOG.info("     #######################################################################")
            show_step(int(step))
            with underlay.remote(node_name=steps[step]['node_name']) as remote:
                for x in range(steps[step]['retry']['count']):
                    result = remote.execute(steps[step]['cmd'], verbose=True)
                    if result.exit_code != 0:
                        sleep(steps[step]['retry']['delay'])
                        LOG.info(" ========================= retry...")
                    else:
                        break
