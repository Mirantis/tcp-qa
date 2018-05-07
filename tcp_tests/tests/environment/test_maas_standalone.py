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

import pytest

from tcp_tests import logger

LOG = logger.logger


class TestMaasStandalone(object):
    """Test class for testing TCP deployment"""

    @pytest.mark.fail_snapshot
    def test_maas_bm_provision(self, show_step, hardware, underlay,
                            day1_cfg_config):
        """Test for deploying an mcp dvr environment and check it

        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """

        show_step(1)
        show_step(2)
        show_step(3)

        cfg_node = 'cfg01.cookied-bm-contrail.local'
        ssh_test_key = day1_cfg_config.config.underlay.ssh_keys[0]['public']
        verbose = True

        cfg_admin_iface = next(i for i in hardware.master_nodes[0].interfaces
                               if i.network.name == 'admin')
        admin_net = cfg_admin_iface.network.address_pool.ip_network

        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='maas logout mirantis && '
            'maas login mirantis '
            'http://localhost:5240/MAAS/api/2.0/ '
            'FTvqwe7ybBp68gPar2:5mcctTAXVL8mns4ef4:zrA9LZwu2tMc8BAZpsPUfwWwTyQnAtDN') # noqa

        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="maas mirantis package-repository update main_archive "
                "disabled_pockets=backports,security")

        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="maas mirantis ipranges create "
            "type=dynamic start_ip={start} end_ip={end} "
            "subnet=$(maas mirantis subnets read | jq '.[] | select(.name==\"{net}\") | .id')".format(  # noqa
                start=admin_net[191],
                end=admin_net[253],
                net=admin_net))
        underlay.check_call(node_name=cfg_node, verbose=verbose,
            cmd="maas mirantis vlan update "
            "$(maas mirantis subnets read | jq '.[] | select(.name==\"{net}\") | .vlan.fabric_id') " # noqa
            "0 dhcp_on=True primary_rack='cfg01'".format(net=admin_net))

        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="ssh-keygen -y -f ~root/.ssh/id_rsa > ~root/.ssh/id_rsa.pub")
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='maas mirantis sshkeys create '
                'key="$(cat ~root/.ssh/id_rsa.pub)"')

        r, f = day1_cfg_config.salt.enforce_state('cfg01*', 'maas.machines')
        LOG.info(r)
        LOG.info(f)

        # underlay.check_call(node_name=cfg_node, verbose=verbose,
        #                     cmd='salt-call state.sls maas.machines')

        # show_step(8)
        nodes_amount = len(hardware.slave_nodes)
        cmd = """   timeout 1800s bash -c 'hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); while ! [ $(echo "$hosts" | wc -w) -eq {amount} ]; do echo "Ready hosts:\n$hosts"; sleep 30; hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); done '   """.format(amount=nodes_amount)  # noqa
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-key')
        # show_step(9)
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='salt-call state.sls maas.machines.deploy')
        # show_step(10)
        underlay.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd='salt-call state.sls maas.machines.wait_for_deployed')
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-key')

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

        result = \
            day1_cfg_config.salt.get_pillar(cfg_node,
                                            '_param:jenkins_salt_api_url')
        result = result[0].get(cfg_node)

        jenkins = JenkinsClient(
            host='http://{host}:8081'.format(
                host=day1_cfg_config.config.salt.salt_master_host),
            username='admin',
            password='r00tme')
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = result
        params['STACK_INSTALL'] = "core,openstack,ovs"
        build = jenkins.run_build('deploy_openstack', params)

        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 2)

        assert \
            jenkins.build_info(
                name=build[0], build_id=build[1])['result'] == 'SUCCESS', \
            "Deploy openstack was failed"

        openstack = managers.openstack_manager.OpenstackManager(
            day1_cfg_config.config, underlay, hardware,
            day1_cfg_config.salt)

        if settings.RUN_TEMPEST:
            openstack.run_tempest(pattern=settings.PATTERN)
            openstack.download_tempest_report()

        LOG.info("*************** DONE **************")


    @pytest.mark.fail_snapshot
    def test_install_maas_standalone(self, config, underlay):
        """Install a VM with standalone maas

        Before using, please set the correct roles and timeout:

            export ROLES='["maas_master"]'
            export BOOTSTRAP_TIMEOUT=900

        , and unset these variables after the bootstrap is completed.

        Scenario:
            1. Install MaaS service and helper services
            2. Download Ubuntu cloud image and calculate MD5
            3. export environment variables to further use

        """

        nodes = underlay.node_names()
        host = underlay.host_by_node_name(nodes[0])
        maas_url = 'http://{0}:5240/'.format(host)
        LOG.info("MaaS url: {}".format(maas_url))
