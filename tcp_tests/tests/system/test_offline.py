#    Copyright 2017 Mirantis, Inc.
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
# import pytest
import time

from collections import Counter

from tcp_tests import logger
from tcp_tests.managers.jenkins.client import JenkinsClient
from tcp_tests import settings

from tcp_tests import managers

LOG = logger.logger


class TestOfflineDeployment(object):
    """docstring for TestOfflineDeployment"""

    def test_deploy_day1(self, show_step, config, underlay, hardware,
                         common_services_deployed, salt_deployed):
        """Test for deploying an mcp from day01 images

        Scenario:
            1. Wait salt master
            2. Addition config of MaaS
            3. Wait dhcpd server
            4. Start comissioning node via MaaS
            5. Wait of comissioning node by MaaS
            6. Start deploing node via MaaS
            7. Wait of deploing node by
            8. Accept all keys
            9. Configure and baremetal nodes after MaaS deployment
            10. Run deploy OS job

        """
        # group = hardware._get_default_node_group()
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        cfg_node = 'cfg01.offline-ocata-vxlan.local'
        tempest_node = 'gtw01.offline-ocata-vxlan.local'
        verbose = True
        ssh_test_key = config.underlay.ssh_keys[0]['public']

        show_step(1)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="""timeout 300s /bin/bash -c """
                """'while ! salt-call test.ping; do """
                """echo "salt master still isnt running"; sleep 10; done'"""
        )  # noqa

        show_step(2)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt-call saltutil.sync_all')

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="salt '*' ssh.set_auth_key root '{}'".format(ssh_test_key))
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt "*" ssh.set_auth_key root '
                '"$(ssh-keygen -y -f ~/.ssh/id_rsa | cut -d " " -f 2)"')
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="salt '*' ssh.set_auth_key ubuntu '{}'".format(ssh_test_key))
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt "*" ssh.set_auth_key ubuntu '
                '"$(ssh-keygen -y -f ~/.ssh/id_rsa | cut -d " " -f 2)"')

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt-call state.sls maas.region')
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='maas logout mirantis && '
            'maas login mirantis '
            'http://localhost:5240/MAAS/api/2.0/ '
            'FTvqwe7ybBp68gPar2:5mcctTAXVL8mns4ef4:zrA9LZwu2tMc8BAZpsPUfwWwTyQnAtDN'  # noqa
        )

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="maas mirantis maas set-config "
                "name=upstream_dns value='10.10.0.15 8.8.8.8 8.8.4.4'")

        # underlay.check_call(
        #     node_name=cfg_node,
        #     verbose=verbose,
        #     cmd="maas mirantis ipranges create "
        #         "type=dynamic start_ip=10.10.191.255 end_ip=10.10.255.254 "
        #         "subnet=$(maas mirantis subnets read | jq '.[] | "
        #         "select(.name==\"10.10.0.0/16\") | .id')")

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="maas mirantis vlan update "
                "$(maas mirantis subnets read | jq '.[] | "
                "select(.name==\"10.10.0.0/16\") | .vlan.fabric_id') "
                "0 dhcp_on=True primary_rack='cfg01'")

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="ssh-keygen -y -f ~root/.ssh/id_rsa > ~root/.ssh/id_rsa.pub")
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='maas mirantis sshkeys create '
                'key="$(cat ~root/.ssh/id_rsa.pub)"')

        show_step(3)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="""timeout 90s /bin/bash -c 'while ! pidof dhcpd; do """
                """echo "dhcpd still isnt running"; sleep 10; done'""")

        show_step(4)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt-call state.sls maas.machines')
        show_step(5)
        cmd = """   timeout 600s bash -c 'hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); while ! [ $(echo "$hosts" | wc -w) -eq 10 ]; do echo "Ready hosts:\n$hosts"; sleep 30; hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); done '   """  # noqa
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)
        underlay.check_call(
            node_name=cfg_node, verbose=verbose, cmd='salt-key')
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt-call state.sls maas.machines.assign_ip')
        show_step(6)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt-call state.sls maas.machines.deploy')
        show_step(7)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt-call state.sls maas.machines.wait_for_deployed')
        underlay.check_call(
            node_name=cfg_node, verbose=verbose, cmd='salt-key')

        show_step(8)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            expected=[0, 1],
            cmd='salt-key -A -y --include-denied --include-rejected')
        underlay.check_call(
            node_name=cfg_node, verbose=verbose, cmd='salt-key')

        show_step(9)
        cmd = "salt '*' saltutil.refresh_pillar"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)
        cmd = "salt '*' saltutil.sync_all"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        underlay.check_call(
            node_name=cfg_node, verbose=verbose, cmd="reclass-salt --top")

        cmd = "salt -C " \
              "'I@salt:control or I@nova:compute or I@neutron:gateway' " \
              "cmd.run 'touch /run/is_rebooted'"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        cmd = "salt --async -C " \
              "'I@salt:control' cmd.run 'salt-call state.sls " \
              "linux.system.user,openssh,linux.network;reboot'"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        cmd = "salt --async -C " \
              "'I@nova:compute' cmd.run 'salt-call state.sls " \
              "linux.system.user,openssh,linux.network;reboot'"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        cmd = "salt --async -C " \
              "'I@neutron:gateway' cmd.run 'salt-call state.sls " \
              "linux.system.user,openssh,linux.network;reboot'"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        time.sleep(360)  # TODO: Add ssh waiter

        cmd = "salt -C " \
              "'I@salt:control or I@nova:compute or I@neutron:gateway'" \
              " test.ping"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        cmd = """salt -C """ \
              """'I@salt:control or I@nova:compute or I@neutron:gateway' """ \
              """cmd.run '[ -f "/run/is_rebooted" ] && """ \
              """echo "Has not been rebooted!" || echo "Rebooted"' """
        ret = underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)
        count = Counter(ret['stdout_str'].split())

        assert count['Rebooted'] == 10, "Should be rebooted 10 baremetal nodes"

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="salt '*' ssh.set_auth_key root '{}'".format(ssh_test_key))
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt "*" ssh.set_auth_key root '
                '"$(ssh-keygen -y -f ~/.ssh/id_rsa | cut -d " " -f 2)"')
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="salt '*' ssh.set_auth_key ubuntu '{}'".format(ssh_test_key))
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt "*" ssh.set_auth_key ubuntu '
                '"$(ssh-keygen -y -f ~/.ssh/id_rsa | cut -d " " -f 2)"')

        salt_api = \
            salt_deployed.get_pillar(cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)

        show_step(10)
        jenkins = JenkinsClient(
            host='http://172.16.44.33:8081',
            username='admin',
            password='r00tme')
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        build = jenkins.run_build('deploy_openstack', params)

        jenkins.wait_end_of_build(
            name=build[0], build_id=build[1], timeout=60 * 60 * 2)

        with open("{path}/cfg01_jenkins_deploy_openstack_console.log".format(
                path=settings.LOGS_DIR), 'w') as f:
            LOG.info("Save jenkins console log")
            console_log = \
                jenkins.get_build_output('deploy_openstack', build[1])
            f.write(console_log)

        assert \
            jenkins.build_info(
                name=build[0], build_id=build[1])['result'] == 'SUCCESS', \
            "Deploy openstack was failed"

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="salt '*' ssh.set_auth_key root '{}'".format(ssh_test_key))
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt "*" ssh.set_auth_key root '
                '"$(ssh-keygen -y -f ~/.ssh/id_rsa | cut -d " " -f 2)"')
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="salt '*' ssh.set_auth_key ubuntu '{}'".format(ssh_test_key))
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd='salt "*" ssh.set_auth_key ubuntu '
                '"$(ssh-keygen -y -f ~/.ssh/id_rsa | cut -d " " -f 2)"')

        salt_nodes = salt_deployed.get_ssh_data()
        nodes_list = \
            [node for node in salt_nodes
             if not any(node['node_name'] == n['node_name']
                        for n in config.underlay.ssh)]
        config.underlay.ssh = config.underlay.ssh + nodes_list
        underlay.add_config_ssh(nodes_list)

        time.sleep(120)  # debug sleep
        cmd = "salt '*' test.ping"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        openstack = managers.openstack_manager.OpenstackManager(
            config, underlay, hardware, salt_deployed)

        if settings.RUN_TEMPEST:
            openstack.run_tempest(
                pattern=settings.PATTERN,
                node_name=tempest_node)
            openstack.download_tempest_report()
