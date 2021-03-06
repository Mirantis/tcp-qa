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
import pytest
import time
import socket
import urlparse

from tcp_tests import logger
from tcp_tests.managers.jenkins.client import JenkinsClient
from tcp_tests import settings

from tcp_tests import managers

LOG = logger.logger


class TestOfflineDeployment(object):
    """docstring for TestOfflineDeployment"""

    @pytest.mark.day1_underlay
    def test_maas_provision(self, show_step, hardware, underlay,
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

        cfg_node = 'cfg01.virtual-mcp-pike-dvr.local'
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

        # show_step(8)
        # nodes_amount = len(hardware.slave_nodes)
        # cmd = """   timeout 600s bash -c 'hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); while ! [ $(echo "$hosts" | wc -w) -eq {amount} ]; do echo "Ready hosts:\n$hosts"; sleep 30; hosts=$(maas mirantis nodes read | jq -r ".[] | select(.node_type_name==\\"Machine\\") | select(.status_name==\\"Ready\\") | .hostname "); done '   """.format(amount=nodes_amount)  # noqa
        cmd = """salt-call state.sls maas.machines.wait_for_ready"""
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)
        underlay.check_call(node_name=cfg_node, verbose=verbose,
                            cmd='salt-key')

        r, f = day1_cfg_config.salt.enforce_state(
            'cfg01*',
            'maas.machines.assign_ip')
        LOG.info(r)
        LOG.info(f)

        r, f = day1_cfg_config.salt.enforce_state(
            'cfg01*',
            'maas.machines.storage')
        LOG.info(r)
        LOG.info(f)

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

    def test_deploy_day1_pike(self, show_step, config, underlay, hardware,
                              core_deployed, salt_deployed, tempest_actions):
        """Test for deploying an mcp from day01 images

        Scenario:
            1. Wait salt master
            2. Run deploy OS job
            3. Add test and root keys
            2. Run deploy CVP sanity job

        """
        # group = hardware._get_default_node_group()
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        cfg_node = 'cfg01.mcp-offline-vxlan.local'
        verbose = True
        ssh_test_key = config.underlay.ssh_keys[0]['public']

        show_step(1)
        underlay.check_call(
            node_name=cfg_node,
            verbose=verbose,
            cmd="""timeout 300s /bin/bash -c """
                """'while ! salt-call test.ping; do """
                """echo "salt master still isnt running"; sleep 10; done'"""
        )

        show_step(2)

        salt_api = \
            salt_deployed.get_pillar(cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)

        jenkins = JenkinsClient(
            host='http://172.16.44.33:8081',
            username='admin',
            password='r00tme')
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        if settings.STACK_INSTALL:
            params['STACK_INSTALL'] = settings.STACK_INSTALL
        else:
            params['STACK_INSTALL'] = \
                'core,kvm,ceph,cicd,ovs,openstack,stacklight,finalize'
        params['STATIC_MGMT_NETWORK'] = 'true'
        build = jenkins.run_build('deploy_openstack', params)

        LOG.info("Take a look deploy progress here - %s. Build #%s",
                 "http://172.16.44.33:8081/job/deploy_openstack/", build[1])

        jenkins.wait_end_of_build(
            name=build[0], build_id=build[1], timeout=60 * 60 * 5)

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

        show_step(3)
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

        salt_deployed.update_ssh_data_from_minions()

        show_step(4)
        try:
            maas_minion_id = salt_deployed.get_single_pillar(
                tgt='I@maas:cluster or I@maas:region',
                pillar="__reclass__:nodename")
            ntp_skipped_nodes = 'ntp_skipped_nodes={0}'.format(maas_minion_id)
        except LookupError:
            ntp_skipped_nodes = ''

        params = jenkins.make_defults_params('cvp-sanity')
        params['TESTS_SETTINGS'] = (
            'drivetrain_version={0};{1}'
            .format(settings.MCP_VERSION, ntp_skipped_nodes))
        build = jenkins.run_build('cvp-sanity', params)
        LOG.info("Take a look test progress here - %s. Build #%s",
                 "http://172.16.44.33:8081/job/cvp-sanity/", build[1])

        jenkins.wait_end_of_build(
            name=build[0], build_id=build[1], timeout=60 * 60 * 5)

        assert \
            jenkins.build_info(
                name=build[0], build_id=build[1])['result'] == 'SUCCESS', \
            "CVP sanity was failed"

        time.sleep(120)  # debug sleep
        cmd = "salt '*' test.ping"
        underlay.check_call(node_name=cfg_node, verbose=verbose, cmd=cmd)

        if settings.RUN_TEMPEST:
            pillar = tempest_actions.runtest_pillar
            params = [
                'glance_image_cirros_location',
                'glance_image_fedora_location',
                'glance_image_manila_location']

            urls = []
            for p in params:
                url = pillar.get('parameters', {}).get('_param', {}).get(p)
                if url:
                    urls.append(url)

            LOG.info("Found url with images - %s", urls)

            hosts = set()
            hosts.add(settings.TEMPEST_IMAGE.split('/')[0])
            for u in urls:
                host = urlparse.urlparse(u)
                hosts.add(host.netloc.split(':')[0])  # drop port if exists

            records = []
            for h in hosts:
                ip = socket.gethostbyname(h)
                records.append((ip, h))

            for ip, h in records:
                salt_deployed.local(cfg_node, 'hosts.add_host', args=(ip, h))

            tempest_actions.prepare_and_run_tempest()

    test_deploy_day1_queens = test_deploy_day1_pike
