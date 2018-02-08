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

from tcp_tests import logger
from tcp_tests.managers.jenkins.client import JenkinsClient

LOG = logger.logger


class TestOfflineDeployment(object):
    """docstring for TestOfflineDeployment"""

    def test_deploy_day1(self, show_step, underlay, common_services_deployed,
                         salt_deployed):
        """Test for deploying an mcp from day01 images

        Scenario:
            1. Approve local ssh key to jenkins
            2. Boot CFG and APT virtual machines
            3. Setup jq
            4. Wait salt master
            5. Addition config of MaaS
            6. Wait dhcpd server
            7. Start comissioning node via MaaS
            8. Wait of comissioning node by MaaS
            9. Start deploing node via MaaS
            10. Wait of deploing node by
            11. Accept all keys
            12. Run deploy OS job

        """
        # group = hardware._get_default_node_group()
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        cfg_node = 'cfg01.offline-ocata-vxlan.local'
        verbose = True

        # show_step(1)
        # cmd = ("mkdir -p /var/lib/jenkins/.ssh && "
        #        "ssh-keyscan cfg01 > /var/lib/jenkins/.ssh/known_hosts && "
        #        "chown jenkins /var/lib/jenkins/.ssh/known_hosts")
        # underlay.check_call(
        #     node_name=cfg_node, verbose=verbose,
        #     cmd=cmd)

        # show_step(2)
        # underlay.check_call(node_name=cfg_node, verbose=verbose,
        #                     cmd='salt-key')

        # show_step(3)
        # underlay.check_call(node_name=cfg_node, verbose=verbose,
        #                     cmd='apt install -y jq')

        show_step(4)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="""timeout 300s /bin/bash -c 'while ! salt-call test.ping; do echo "salt master still isnt running"; sleep 10; done'""")  # noqa

        show_step(5)
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-call saltutil.sync_all')
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-call state.sls maas.region')
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='maas logout mirantis && '
            'maas login mirantis '
            'http://localhost/MAAS/api/2.0/ '
            'FTvqwe7ybBp68gPar2:5mcctTAXVL8mns4ef4:zrA9LZwu2tMc8BAZpsPUfwWwTyQnAtDN') # noqa

        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="maas mirantis ipranges create "
            "type=dynamic start_ip=10.10.191.255 end_ip=10.10.255.254 "
            "subnet=$(maas mirantis subnets read | jq '.[] | select(.name==\"10.10.0.0/16\") | .id')") # noqa
        underlay.check_call(node_name=cfg_node, verbose=verbose,
            cmd="maas mirantis vlan update "
            "$(maas mirantis subnets read | jq '.[] | select(.name==\"10.10.0.0/16\") | .vlan.fabric_id') " # noqa
            "0 dhcp_on=True primary_rack='cfg01'")

        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="ssh-keygen -y -f ~root/.ssh/id_rsa > ~root/.ssh/id_rsa.pub")
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='maas mirantis sshkeys create '
                'key="$(cat ~root/.ssh/id_rsa.pub)"')

        show_step(6)
        underlay.check_call(node_name=cfg_node, verbose=verbose,
            cmd="""timeout 90s /bin/bash -c 'while ! pidof dhcpd; do  echo "dhcpd still isnt running"; sleep 10; done'""") # noqa

        show_step(7)
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-call state.sls maas.machines')
        show_step(8)
        cmd = """   timeout 600s bash -c 'hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); while ! [ $(echo "$hosts" | wc -w) -eq 10 ]; do echo "Ready hosts:\n$hosts"; sleep 30; hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); done '   """ # noqa
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-key')
        show_step(9)
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='salt-call state.sls maas.machines.deploy')
        show_step(10)
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='salt-call state.sls maas.machines.wait_for_deployed')
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-key')

        show_step(11)
        underlay.check_call(
            node_name=cfg_node, verbose=verbose, expected=[0, 1],
            cmd='salt-key -A -y --include-denied --include-rejected')
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='salt-key')

        salt_api = \
            salt_deployed.get_pillar(cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)

        show_step(12)
        jenkins = JenkinsClient(
            host='http://172.16.44.33:8081',
            username='admin',
            password='r00tme')
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        build = jenkins.run_build('deploy_openstack', params)

        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 2)

        assert \
            jenkins.build_info(
                name=build[0], build_id=build[1])['result'] == 'SUCCESS', \
            "Deploy openstack was failed"
