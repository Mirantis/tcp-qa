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
    salt_cmd = 'salt --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    salt_call_cmd = 'salt-call --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    #salt_cmd = 'salt --state-output=terse --state-verbose=False '  # For reduced output
    #salt_call_cmd = 'salt-call --state-output=terse --state-verbose=False '  # For reduced output

    steps_mk22_advanced_lab = [
        # Prepare salt services and nodes settings
        {
            'description': "Run 'linux' formula on cfg01",
            'cmd': salt_call_cmd + "state.sls linux",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Run 'openssh' formula on cfg01",
            'cmd': (salt_call_cmd + "state.sls openssh;"
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
            'cmd': salt_call_cmd + " state.sls salt",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': True,
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
            'cmd': salt_call_cmd + "state.sls reclass.storage",
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


        # Bootstrap all nodes
        {
            'description': "Configure linux on controllers",
            'cmd': salt_cmd + "'*' state.sls linux",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 5, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure openssh on controllers",
            'cmd': (salt_cmd + "-C '* and not cfg*' state.sls openssh;"
                    + salt_cmd + "-C '* and not cfg*' cmd.run "
                    "\"sed -i 's/PasswordAuthentication no/"
                    "PasswordAuthentication yes/' /etc/ssh/sshd_config && "
                    "service ssh restart\""),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("*Workaround* for the bug"
                            " https://mirantis.jira.com/browse/PROD-8025"),
            'cmd': (salt_cmd + "'*' cmd.run 'apt-get update &&"
                    " apt-get -y upgrade'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("*Workaround* for the bug"
                            " https://mirantis.jira.com/browse/PROD-8021"),
            'cmd': (salt_cmd + "'*' cmd.run 'apt-get -y install"
                    " linux-image-extra-$(uname -r)'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': ("*Workaround* for the bug"
                            " https://mirantis.jira.com/browse/PROD-XXXXX"),
            'cmd': (salt_cmd + "'*' cmd.run 'apt-get -y install python-requests'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure salt.minion on controllers",
            'cmd': salt_cmd + "'*' state.sls salt.minion",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure ntp on controllers",
            'cmd': salt_cmd + "'*' state.sls ntp",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 5, 'delay': 10},
            'skip_fail': False,
        },

        # Install support services
        {
            'description': "Install keepalived on primary controller",
            'cmd': salt_cmd + "'ctl01*' state.sls keepalived",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install keepalived on other controllers",
            'cmd': salt_cmd + "'ctl*' state.sls keepalived -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check the VIP",
            # First grep finds the IP, second is to get the correct exit code
            'cmd': (salt_cmd + "'ctl*' cmd.run 'ip a | grep 172.16.10.254' |"
                    " grep -B1 172.16.10.254"),
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
            'cmd': salt_cmd + "'ctl01*' state.sls glusterfs.server.setup",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Setup glusterfs on other controllers",
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.server.setup -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check the gluster status",
            'cmd': salt_cmd + "'ctl01*' cmd.run 'gluster peer status; gluster volume status'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
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
            'description': "Check the rabbitmq status",
            'cmd': salt_cmd + "'ctl*' cmd.run 'rabbitmqctl cluster_status'",
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
            'cmd': salt_cmd + "'ctl*' state.sls galera",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check mysql status",
            'cmd': salt_cmd + "'ctl*' mysql.status",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': True,
        },




        {
            'description': "Install haproxy on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls haproxy",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check haproxy status",
            'cmd': salt_cmd + "'ctl*' service.status haproxy",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },


        {
            'description': "Install memcached on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls memcached",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },


        # Install OpenStack control services


        {
            'description': "Install keystone on primary controller",
            'cmd': salt_cmd + "'ctl01*' state.sls keystone",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install keystone on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls keystone -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Populate keystone services/tenants/admins",
            'cmd': salt_call_cmd + "state.sls keystone.client",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check keystone service-list",
            'cmd': salt_cmd + "'ctl01*' cmd.run '. /root/keystonerc; keystone service-list'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },



        {
            'description': "Install glance on primary controller",
            'cmd': salt_cmd + "'ctl01*' state.sls glance",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install glance on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls glance -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure glusterfs.client on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls glusterfs.client",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Configure(re-install) keystone on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls keystone -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check glance image-list",
            'cmd': salt_cmd + "'ctl01*' cmd.run '. /root/keystonerc; glance image-list'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },



        {
            'description': "Install cinder on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls cinder -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check cinder list",
            'cmd': salt_cmd + "'ctl01*' cmd.run '. /root/keystonerc; cinder list'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },


        {
            'description': "Install nova on ctl01",
            'cmd': salt_cmd + "'ctl01*' state.sls nova",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install nova on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls nova",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check nova service-list",
            'cmd': salt_cmd + "'ctl01*' cmd.run '. /root/keystonerc; nova service-list'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },


        {
            'description': "Install neutron on ctl01",
            'cmd': salt_cmd + "'ctl01*' state.sls neutron",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Install neutron on all controllers",
            'cmd': salt_cmd + "'ctl*' state.sls neutron",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check neutron agent-list",
            'cmd': salt_cmd + "'ctl01*' cmd.run '. /root/keystonerc; neutron agent-list'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },


        {
            'description': "Deploy dashboard on prx*",
            'cmd': salt_cmd + "'prx*' state.apply",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': True,
        },


        {
            'description': "Deploy nginx proxy",
            'cmd': salt_cmd + "'cfg*' state.sls nginx",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': True,
        },



        # Install contrail on controllers
        {
            'description': "Install contrail database on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls opencontrail.database -b 1",
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
        {
            'description': "Install contrail database on controllers",
            'cmd': salt_cmd + "'ctl*' state.sls opencontrail -b 1",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check contrail status",
            'cmd': (salt_cmd + "'ctl01*' cmd.run '. /root/keystonerc;"
                    " contrail-status; neutron net-list; nova net-list'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Add contrail bgp router on ctl01",
            'cmd': (salt_cmd + "'ctl01*' cmd.run "
                    "'/usr/share/contrail-utils/provision_control.py"
                    " --oper add"
                    " --api_server_ip 172.16.10.254"
                    " --api_server_port 8082"
                    " --host_name ctl01"
                    " --host_ip 172.16.10.101"
                    " --router_asn 64512"
                    " --admin_user admin"
                    " --admin_password workshop"
                    " --admin_tenant_name admin"
                    "'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Add contrail bgp router on ctl02",
            'cmd': (salt_cmd + "'ctl02*' cmd.run "
                    "'/usr/share/contrail-utils/provision_control.py"
                    " --oper add"
                    " --api_server_ip 172.16.10.254"
                    " --api_server_port 8082"
                    " --host_name ctl02"
                    " --host_ip 172.16.10.102"
                    " --router_asn 64512"
                    " --admin_user admin"
                    " --admin_password workshop"
                    " --admin_tenant_name admin"
                    "'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Add contrail bgp router on ctl03",
            'cmd': (salt_cmd + "'ctl03*' cmd.run "
                    "'/usr/share/contrail-utils/provision_control.py"
                    " --oper add"
                    " --api_server_ip 172.16.10.254"
                    " --api_server_port 8082"
                    " --host_name ctl03"
                    " --host_ip 172.16.10.103"
                    " --router_asn 64512"
                    " --admin_user admin"
                    " --admin_password workshop"
                    " --admin_tenant_name admin"
                    "'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },


        # Install compute node
        {
            'description': "Apply formulas for compute node",
            'cmd': salt_cmd + "'cmp*' state.apply",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Re-apply(as in doc) formulas for compute node",
            'cmd': salt_cmd + "'cmp*' state.apply",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Add vrouter for cmp01",
            'cmd': (salt_cmd + "'ctl01*' cmd.run "
                    "'/usr/share/contrail-utils/provision_vrouter.py"
                    " --oper add"
                    " --host_name cmp01"
                    " --host_ip 172.16.10.105"
                    " --api_server_ip 172.16.10.254"
                    " --api_server_port 8082"
                    " --admin_user admin"
                    " --admin_password workshop"
                    " --admin_tenant_name admin"
                    "'"),
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Reboot compute nodes",
            'cmd': salt_cmd + "'cmp*' system.reboot",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check IP on computes",
            'cmd': salt_cmd + "'cmp*' cmd.run 'ip a'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
        {
            'description': "Check contrail status on computes",
            'cmd': salt_cmd + "'cmp*' cmd.run 'contrail-status'",
            'node_name': 'cfg01.mk22-lab-advanced.local',  # hardcoded for now
            'retry': {'count': 3, 'delay': 5},
            'skip_fail': False,
        },
    ]


    @pytest.mark.steps(steps_mk22_advanced_lab)
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
                    time.sleep(3)
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
                            "salt-call pillar.items",
                            'active (running)') # Hardcoded for now
                        tcp_actions.check_salt_service(
                            "salt-minion",
                            "cfg01.mk22-lab-advanced.local",
                            "salt 'cfg01*' pillar.items",
                            "active (running)") # Hardcoded for now
                        break

                    if x == 1 and step['skip_fail'] == False:
                        # In the last retry iteration, raise an exception
                        raise Exception("Step '{0}' failed"
                                        .format(step['description']))
