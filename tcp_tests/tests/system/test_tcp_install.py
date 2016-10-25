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
import time

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
        1: {
            'cmd': salt_cmd + "'cfg01*' state.sls linux",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        2: {
            'cmd': (salt_cmd + "'cfg01*' state.sls openssh;"
                    "sed -i 's/PasswordAuthentication no/"
                    "PasswordAuthentication yes/' "
                    "/etc/ssh/sshd_config && service ssh restart"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        3: {
            'cmd': "echo '    StrictHostKeyChecking no' >> /root/.ssh/config",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 1, 'delay': 1},
            'skip_fail': False,
        },
        4: {
            'cmd': salt_cmd + "'cfg01*' state.sls salt",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        5: {
            'cmd': salt_cmd + "'cfg01*' state.sls reclass.storage",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        6: {
            'cmd': salt_cmd + "'*' saltutil.refresh_pillar",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        7: {
            'cmd': salt_cmd + "'ctl*' state.sls ntp",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        8: {
            'cmd': (salt_cmd + "'ctl*' state.sls linux,salt.minion,openssh;"
                    + salt_cmd + "'ctl*' cmd.run "
                    "\"sed -i 's/PasswordAuthentication no/"
                    "PasswordAuthentication yes/' /etc/ssh/sshd_config && "
                    "service ssh restart\""),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        9: {
            'cmd': salt_cmd + "'ctl01*' state.sls keepalived",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        10: {
            'cmd': salt_cmd + "'ctl01*' cmd.run 'ip a'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        11: {
            'cmd': salt_cmd + "'ctl0[23].*' state.sls keepalived",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        12: {
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.server.service",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        13: {
            'cmd': salt_call_cmd + "state.sls glusterfs.server.setup",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        14: {
            'cmd': "gluster peer status",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        15: {
            'cmd': "gluster volume status",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        16: {
            'cmd': salt_cmd + "'ctl*' state.sls rabbitmq",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        17: {
            'cmd': "apt-get -y --force-yes install salt-formula-galera",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        18: {
            'cmd': salt_call_cmd + "state.sls galera",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        19: {
            'cmd': salt_cmd + "'ctl0[23]*' state.sls galera",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        20: {
            'cmd': salt_cmd + "'ctl01*'  mysql.status | grep -A1 'wsrep_incoming_addresses:'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        21: {
            'cmd': salt_cmd + "'ctl*' state.sls haproxy",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        22: {
            'cmd': salt_cmd + "'ctl*' cmd.run 'netstat -tulnp | grep 3306'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        23: {
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        24: {
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl02.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        25: {
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl03.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        26: {
            'cmd': "source ~/keystonerc; keystone user-list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        27: {
            'cmd': "source ~/keystonerc; keystone tenant-list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        28: {
            'cmd': "source ~/keystonerc; keystone endpoint-list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        29: {
            'cmd': salt_cmd + "'ctl*' state.sls glance",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        30: {
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.client",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        31: {
            'cmd': salt_cmd + "'ctl*' cmd.run 'df -h'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        32: {
            'cmd': salt_call_cmd + "state.sls keystone",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        33: {
            'cmd': ("source ~/keystonerc;"
                    "wget http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-i386-disk.img;"
                    "glance image-create --name 'cirros-0.3.4'"
                    "  --disk-format qcow2 --container-format bare"
                    "  --progress --file /root/cirros-0.3.4-i386-disk.img;"
                    "glance image-list;"),
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        34: {
            'cmd': salt_cmd + "'ctl*' cmd.run 'ls -al /var/lib/keystone/fernet-keys' ",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        35: {
            'cmd': salt_cmd + "'ctl*' cinder",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        36: {
            'cmd': salt_cmd + "'ctl*' nova",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        37: {
            'cmd': "source ~/keystonerc; cinder list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        38: {
            'cmd': "source ~/keystonerc; nova-manage service list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        39: {
            'cmd': "source ~/keystonerc; nova list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        40: {
            'cmd': salt_cmd + "'ctl*' state.sls neutron",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        41: {
            'cmd': ("source ~/keystonerc;"
                    "neutron net-create --router:external=true  --shared external;"
                    "neutron subnet-create external 10.177.0.0/24;"
                    "neutron floatingip-create;"),
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        42: {
            'cmd': salt_cmd + "'ctl*' state.sls opencontrail.database",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        43: {
            'cmd': ("nodetool status;"
                    "nodetool compactionstats;"
                    "nodetool describecluster;"),
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
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
            17. *Workaround* Update salt-formula-galera on config node to the latest version
            18. Install Galera on primary controller
            19. Install Galera on other controllers
            20. Check Galera addresses
            21. Install haproxy on all controllers
            22. Check haproxy on all controllers with Galera port
            23. Install memcached and keystone on ctl01
            24. Install memcached and keystone on ctl02
            25. Install memcached and keystone on ctl03
            26. Check keystone user-list
            27. Check keystone tenant-list
            28. Check keystone endpoint-list
            29. Install glance on controllers
            30. Install glusterfs on controllers
            31. Check that glusterfs was added on controllers
            32. *Workaround* Re-run keystone formula on ctl01 to create fernet keys
            33. Check glance on ctl01
            34. Check keystone fernet keys on controllers
            35. Install cinder on controllers
            36. Install nova on controllers
            37. Check cinder status
            38. Check nova services status
            39. Check nova status
            40. Install neutron on controllers
            41. Create a neutron subnet
            42. Install contrail database on controllers
            43. Check cassandra status on ctl01

        """
        for step in sorted(steps):
            LOG.info("     #######################################################################")
            show_step(int(step))
            with underlay.remote(node_name=steps[step]['node_name']) as remote:
                for x in range(steps[step]['retry']['count']):

                    time.sleep(5)

                    result = remote.execute(steps[step]['cmd'], verbose=True)

                    # Workaround of exit code 0 from salt in case of failures
                    failed = 0
                    for s in result['stdout']:
                        if s.startswith("Failed:"):
                            failed += int(s.split("Failed:")[1])

                    if result.exit_code != 0:
                        time.sleep(steps[step]['retry']['delay'])
                        LOG.info(" ========================= retry...")
                    elif failed != 0:
                        LOG.error(" ================= SALT returned exit code = 0 while there are failed modules!")
                        LOG.info(" ========================= retry...")
                    else:
                        # Workarounds for crashed services
                        tcp_actions.check_salt_service("salt-master", "cfg01.mk22-lab-advanced.local", "salt-call pillar.items") # Hardcoded for now
                        tcp_actions.check_salt_service("salt-minion", "cfg01.mk22-lab-advanced.local", "salt 'cfg01*' pillar.items") # Hardcoded for now
                        break

                    if x == 1 and steps[step]['skip_fail'] == False:
                        # In the last retry iteration, raise an exception
                        raise Exception("Step {0} failed".format(step))
