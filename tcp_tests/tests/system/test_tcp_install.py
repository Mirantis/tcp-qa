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

    #salt_cmd = 'salt -l debug '  # For debug output
    #salt_call_cmd = 'salt-call -l debug '  # For debug output
    salt_cmd = 'salt --state-output=mixed --state-verbose=False '  # For cause only output
    salt_call_cmd = 'salt-call --state-output=mixed --state-verbose=False '  # For cause only output
    #salt_cmd = 'salt --state-output=terse --state-verbose=False '  # For reduced output
    #salt_call_cmd = 'salt-call --state-output=terse --state-verbose=False '  # For reduced output


    steps_mk22_lab_advanced = [
        {
            'description': "Run 'linux' formula on cfg01",
            'cmd': salt_cmd + "'cfg01*' state.sls linux",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Run 'openssh' formula on cfg01",
            'cmd': (salt_cmd + "'cfg01*' state.sls openssh;"
                    "sed -i 's/PasswordAuthentication no/"
                    "PasswordAuthentication yes/' "
                    "/etc/ssh/sshd_config && service ssh restart"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("*Workaround* of the bug"
                            " https://mirantis.jira.com/browse/PROD-7962"),
            'cmd': "echo '    StrictHostKeyChecking no' >> /root/.ssh/config",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 1, 'delay': 1},
            'skip_fail': False,
        },
        {
            'description': "Run 'salt' formula on cfg01",
            'cmd': salt_cmd + "'cfg01*' state.sls salt",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Accept salt keys from all the nodes",
            'cmd': "salt-key -A -y",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 1, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("Generate inventory for all the nodes to the"
                            " /srv/salt/reclass/nodes/_generated"),
            'cmd': salt_cmd + "'cfg01*' state.sls reclass.storage",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Refresh pillars on all minions",
            'cmd': salt_cmd + "'*' saltutil.refresh_pillar",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure ntp on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls ntp",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 5, 'delay': 10},
            'skip_fail': False,
        },
        {
            'description': "Configure linux on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls linux",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 5, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure openssh on controllers",
            'cmd': (salt_cmd + "'ctl*' state.sls openssh;"
                    + salt_cmd + "'ctl*' cmd.run "
                    "\"sed -i 's/PasswordAuthentication no/"
                    "PasswordAuthentication yes/' /etc/ssh/sshd_config && "
                    "service ssh restart\""),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure salt.minion on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls salt.minion",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install keepalived on primary controller",
            'cmd': salt_cmd + "'ctl01*' state.sls keepalived",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Show VIP on primary controller",
            'cmd': salt_cmd + "'ctl01*' cmd.run 'ip a'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install keepalived on other controllers",
            'cmd': salt_cmd + "'ctl0[23].*' state.sls keepalived",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install glusterfs on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.server.service",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Setup glusterfs on primary controller",
            'cmd': salt_call_cmd + "state.sls glusterfs.server.setup",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Show glusterfs peer status",
            'cmd': "gluster peer status",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Show glusterfs volume status",
            'cmd': "gluster volume status",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install RabbitMQ on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls rabbitmq",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("*Workaround* Update salt-formula-galera on"
                            " config node to the latest version"),
            'cmd': "apt-get -y --force-yes install salt-formula-galera",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install Galera on primary controller",
            'cmd': salt_call_cmd + "state.sls galera",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install Galera on other controllers",
            'cmd': salt_cmd + "'ctl0[23]*' state.sls galera",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check Galera addresses",
            'cmd': (salt_cmd + "'ctl01*'  mysql.status |"
                    " grep -A1 'wsrep_incoming_addresses:'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install haproxy on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls haproxy",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check haproxy on all controllers with Galera port",
            'cmd': salt_cmd + "'ctl*' cmd.run 'netstat -tulnp | grep 3306'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install memcached and keystone on ctl01",
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install memcached and keystone on ctl02",
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl02.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install memcached and keystone on ctl03",
            'cmd': salt_call_cmd + "state.sls memcached,keystone",
            'node_name': 'ctl03.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check keystone user-list",
            'cmd': "source ~/keystonerc; keystone user-list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check keystone tenant-list",
            'cmd': "source ~/keystonerc; keystone tenant-list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check keystone endpoint-list",
            'cmd': "source ~/keystonerc; keystone endpoint-list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install glance on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls glance",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install glusterfs on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.client",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check that glusterfs was added on controllers",
            'cmd': salt_cmd + "'ctl*' cmd.run 'df -h'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("*Workaround* Re-run keystone formula on ctl01 to"
                            " create fernet keys"),
            'cmd': salt_call_cmd + "state.sls keystone",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check glance on ctl01",
            'cmd': ("source ~/keystonerc;"
                    "wget http://download.cirros-cloud.net/0.3.4/"
                    "cirros-0.3.4-i386-disk.img;"
                    "glance image-create --name 'cirros-0.3.4'"
                    "  --disk-format qcow2 --container-format bare"
                    "  --progress --file /root/cirros-0.3.4-i386-disk.img;"
                    "glance image-list;"),
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check keystone fernet keys on controllers",
            'cmd': (salt_cmd + "'ctl*' cmd.run 'ls -la"
                    " /var/lib/keystone/fernet-keys' "),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install cinder on controllers",
            'cmd': salt_cmd + "'ctl*' cinder",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install nova on controllers",
            'cmd': salt_cmd + "'ctl*' nova",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check cinder status",
            'cmd': "source ~/keystonerc; cinder list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check nova services status",
            'cmd': "source ~/keystonerc; nova-manage service list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check nova status",
            'cmd': "source ~/keystonerc; nova list",
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install neutron on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls neutron",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Create a neutron subnet",
            'cmd': ("source ~/keystonerc;"
                    "neutron net-create --router:external=true"
                    " --shared external;"
                    "neutron subnet-create external 10.177.0.0/24;"
                    "neutron floatingip-create;"),
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install contrail database on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls opencontrail.database",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check cassandra status on ctl01",
            'cmd': ("nodetool status;"
                    "nodetool compactionstats;"
                    "nodetool describecluster;"),
            'node_name': 'ctl01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
    ]


    @pytest.mark.steps(steps_mk22_lab_advanced)
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    # @pytest.mark.snapshot_needed
    # @pytest.mark.fail_snapshot
    def test_tcp_install_default(self, underlay, tcp_actions, steps, show_step):
        """Test for deploying an tcp environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """
        for n, step in enumerate(steps):
            LOG.info(" ####################################################")
            LOG.info(" *** [ STEP #{0} ] {1} ***"
                     .format(n+1, step['description']))

            with underlay.remote(node_name=step['node_name']) as remote:
                for x in range(step['retry']['count'], 0, -1):

                    result = remote.execute(step['cmd'], verbose=True)

                    # Workaround of exit code 0 from salt in case of failures
                    failed = 0
                    for s in result['stdout']:
                        if s.startswith("Failed:"):
                            failed += int(s.split("Failed:")[1])

                    if result.exit_code != 0:
                        time.sleep(step['retry']['delay'])
                        LOG.info(" === RETRY ({0}/{1}) ========================="
                                 .format(x-1, step['retry']['count']))
                    elif failed != 0:
                        LOG.error(" === SALT returned exit code = 0 while "
                                  "there are failed modules! ===")
                        LOG.info(" === RETRY ({0}/{1}) ======================="
                                 .format(x-1, step['retry']['count']))
                    else:
                        # Workarounds for crashed services
                        tcp_actions.check_salt_service(
                            "salt-master",
                            "cfg01.mk22-lab-advanced.local",
                            "salt-call pillar.items") # Hardcoded for now
                        tcp_actions.check_salt_service(
                            "salt-minion",
                            "cfg01.mk22-lab-advanced.local",
                            "salt 'cfg01*' pillar.items") # Hardcoded for now
                        break

                    if x == 1 and step['skip_fail'] == False:
                        # In the last retry iteration, raise an exception
                        raise Exception("Step '{0}' failed"
                                        .format(step['description']))
