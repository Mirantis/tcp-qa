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

import pytest

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.managers.jenkins.client import JenkinsClient

LOG = logger.logger


@pytest.mark.deploy
class TestMcpInstallOvsPike(object):
    """Test class for testing mcp11 vxlan deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs
    def test_mcp_pike_ovs_install(self, underlay,
                                  openstack_deployed,
                                  openstack_actions,
                                  tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_sl
    def test_mcp_pike_ovs_sl_install(self, underlay, config,
                                     openstack_deployed,
                                     stacklight_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Download SL component tests report
        """
        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        stacklight_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_dvr
    def test_mcp_pike_dvr_install(self,
                                  underlay,
                                  openstack_deployed,
                                  openstack_actions,
                                  tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest
        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_dvr_sl
    def test_mcp_pike_dvr_sl_install(self, underlay, config,
                                     openstack_deployed,
                                     stacklight_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Download SL component tests report
        """

        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        stacklight_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tests
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_mcp_pike_dpdk_install(self, underlay, openstack_deployed,
                                   config, show_step, openstack_actions):
        """Test for deploying an mcp dpdk environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_cookied_ovs_sl
    def test_mcp_pike_cookied_ovs_install(self, underlay,
                                          openstack_deployed,
                                          openstack_actions,
                                          stacklight_deployed,
                                          tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_cookied_ovs_dvr_sl
    def test_mcp_pike_cookied_dvr_install(self,
                                          underlay,
                                          openstack_deployed,
                                          openstack_actions,
                                          stacklight_deployed,
                                          tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_mcp_pike_cookied_dpdk_install(self, underlay,
                                           openstack_deployed,
                                           show_step,
                                           openstack_actions,
                                           tempest_actions):
        """Test for deploying an mcp dpdk environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_l2gw_bgpvpn
    def test_mcp_pike_ovs_l2gw_bgpvpn_install(self, underlay,
                                              openstack_deployed,
                                              openstack_actions):
        """Test for deploying an mcp environment with L2 gateway and BGP VPN
        Neutron extensions enabled and check it
        Scenario:
        1. Prepare VM which emulate VSwitch for L2 GW tests
        2. Prepare salt on hosts
        3. Setup controller nodes
        4. Setup compute nodes
        5. Run tempest

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        registry = 'docker-dev-local.docker.mirantis.net/mirantis/networking'
        name = 'rally-tempest-net-features:latest'

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(
                pattern=settings.PATTERN,
                conf_name='net_features.conf',
                registry='{0}/{1}'.format(registry, name)
            )
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_bm_deploy(self, config, underlay,
                       openstack_deployed,
                       tempest_actions):
        """Test for deploying an mcp environment on baremetal

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.offline_dpdk
    def test_mcp_dpdk_ovs_install(self, underlay,
                                  openstack_deployed,
                                  openstack_actions,
                                  tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()

        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.offline_dpdk
    def test_pipeline_deploy_os_dpdk(self, show_step,
                                     underlay, config, salt_deployed,
                                     tempest_actions,
                                     openstack_actions):
        """Deploy cid, deploys os with pipelines

        Scenario:
            1. Prepare salt on hosts.
            2. Connect to jenkins on cfg01 node
            3. Run deploy on cfg01 node
            4. Connect to jenkins on cid node
            5. Run deploy DT on cid node
            6. Run deploy of os with DT
        """
        show_step(1)
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        show_step(2)
        cfg_node_name = underlay.get_target_node_names(
            target='cfg')[0]
        salt_api = salt_deployed.get_pillar(
            cfg_node_name, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node_name)
        jenkins = JenkinsClient(
            host='http://{}:8081'.format(config.salt.salt_master_host),
            username='admin',
            password='r00tme')
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        params['STACK_INSTALL'] = 'core,cicd'

        show_step(3)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', \
            "Deploy core, cid failed {0}{1}".format(
                jenkins.build_info(name=build[0], build_id=build[1]), result)

        show_step(4)
        cid_node = underlay.get_target_node_names(
            target='cid01')[0]
        salt_output = salt_deployed.get_pillar(
            cid_node, 'jenkins:client:master:password')
        cid_passwd = salt_output[0].get(cid_node)

        pillar = 'keepalived:cluster:instance:cicd_control_vip:address'
        addresses = salt_deployed.get_pillar('cid01*', pillar)
        ip = list(set([ipaddr
                  for item in addresses
                  for node, ipaddr in item.items() if ipaddr]))
        LOG.info('Jenkins ip is {}'.format(ip))
        try:
            assert len(ip) > 0, 'fail to find jenkins ip'
        except AssertionError:
            salt_deployed._salt.local(
                tgt='cid*', fun='cmd.run',
                args='service keepalived restart')
            addresses = salt_deployed.get_pillar('cid01*', pillar)
            ip = list(set([ipaddr
                      for item in addresses
                      for node, ipaddr in item.items() if ipaddr]))
            LOG.info('Jenkins ip is {}'.format(ip))
            assert len(ip) > 0, 'fail to find jenkins ip {}'.format(addresses)

        jenkins = JenkinsClient(
            host='http://{}:8081'.format(ip[0]),
            username='admin',
            password=cid_passwd)
        params['STACK_INSTALL'] = 'ovs,openstack'
        params['SALT_MASTER_URL'] = 'http://{}:6969'.format(
            config.salt.salt_master_host)
        show_step(5)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS',\
            "Deploy openstack was failed with results {0} {1}".format(
                jenkins.build_info(name=build[0], build_id=build[1]),
                result)

        # Prepare resources before test
        steps_path = config.openstack_deploy.openstack_resources_steps_path
        commands = underlay.read_template(steps_path)
        openstack_actions.install(commands)

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest(
                store_run_test_model=False)
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_pipeline_offline_os_dpdk_l2gtw(self, show_step,
                                            underlay, config,
                                            salt_deployed,
                                            tempest_actions,
                                            openstack_actions):
        """Deploy cid, deploys os with pipelines

        Scenario:
            1. Prepare salt on hosts.
            2. Connect to jenkins on cfg01 node
            3. Run deploy on cfg01 node
            4. Connect to jenkins on cid node
            5. Run deploy DT on cid node
            6. Run deploy of os with DT
        """
        show_step(1)
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        show_step(2)
        cfg_node_name = underlay.get_target_node_names(
            target='cfg')[0]
        salt_api = salt_deployed.get_pillar(
            cfg_node_name, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node_name)
        jenkins = JenkinsClient(
            host='http://{}:8081'.format(config.salt.salt_master_host),
            username='admin',
            password='r00tme')
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        params['STACK_INSTALL'] = 'core,cicd'

        show_step(3)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', \
            "Deploy core, cid failed {0}{1}".format(
                jenkins.build_info(name=build[0], build_id=build[1]), result)

        show_step(4)
        cid_node = underlay.get_target_node_names(
            target='cid01')[0]
        salt_output = salt_deployed.get_pillar(
            cid_node, 'jenkins:client:master:password')
        cid_passwd = salt_output[0].get(cid_node)

        pillar = 'keepalived:cluster:instance:cicd_control_vip:address'
        addresses = salt_deployed.get_pillar('cid01*', pillar)
        ip = list(set([ipaddr
                  for item in addresses
                  for node, ipaddr in item.items() if ipaddr]))
        LOG.info('Jenkins ip is {}'.format(ip))
        try:
            assert len(ip) > 0, 'fail to find jenkins ip'
        except AssertionError:
            salt_deployed._salt.local(
                tgt='cid*', fun='cmd.run',
                args='service keepalived restart')
            addresses = salt_deployed.get_pillar('cid01*', pillar)
            ip = list(set([ipaddr
                      for item in addresses
                      for node, ipaddr in item.items() if ipaddr]))
            LOG.info('Jenkins ip is {}'.format(ip))
            assert len(ip) > 0, 'fail to find jenkins ip {}'.format(addresses)

        jenkins = JenkinsClient(
            host='http://{}:8081'.format(ip[0]),
            username='admin',
            password=cid_passwd)
        params['STACK_INSTALL'] = 'ovs,openstack'
        params['SALT_MASTER_URL'] = 'http://{}:6969'.format(
            config.salt.salt_master_host)
        show_step(5)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS',\
            "Deploy openstack was failed with results {0} {1}".format(
                jenkins.build_info(name=build[0], build_id=build[1]),
                result)

        # Prepare resources before test
        steps_path = config.openstack_deploy.openstack_resources_steps_path
        commands = underlay.read_template(steps_path)
        openstack_actions.install(commands)

        registry = 'docker-dev-local.docker.mirantis.net/mirantis/networking'
        name = 'rally-tempest-net-features:latest'

        if settings.RUN_TEMPEST:
            openstack_actions.prepare_and_run_tempest(
                pattern=settings.PATTERN,
                conf_name='net_features.conf',
                registry='{0}/{1}'.format(registry, name),
                store_run_test_model=False
            )
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_offline_barbican_install(self, underlay,
                                      openstack_deployed,
                                      openstack_actions,
                                      tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest(store_run_test_model=False)
        LOG.info("*************** DONE **************")
