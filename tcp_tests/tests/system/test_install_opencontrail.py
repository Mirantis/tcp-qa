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

from tcp_tests.managers.jenkins.client import JenkinsClient
from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


@pytest.mark.deploy
class TestOpenContrail(object):
    """Test class for testing OpenContrail on a TCP lab"""

    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="ctl01.")
    def test_opencontrail_simple(self, config, underlay, salt_deployed,
                                 openstack_deployed, stacklight_deployed,
                                 show_step):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Run tempest
            5. Run SL test
        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            tempest_conf_name = '/var/lib/contrail_fixed_mcp.conf'
            openstack_deployed.run_tempest(target='ctl01',
                                           pattern=settings.PATTERN,
                                           conf_name=tempest_conf_name)
            openstack_deployed.download_tempest_report(stored_node='ctl01')
        # Run SL component tetsts
        if settings.RUN_SL_TESTS:
            show_step(5)
            stacklight_deployed.run_sl_functional_tests(
                'cfg01',
                '/root/stacklight-pytest/stacklight_tests/',
                'tests/prometheus',
                'test_alerts.py')
            show_step(8)
            # Download report
            stacklight_deployed.download_sl_test_report(
                'cfg01',
                '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.with_rally(rally_node="ctl01.")
    def test_opencontrail3_maas(self, config, underlay, salt_actions,
                                openstack_deployed, show_step,
                                stacklight_deployed):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Run tempest
            5. Exporting results
            6. Check docker services
            7. Run SL tests
            8. Download sl tests report
        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            show_step(4)
            openstack_deployed.run_tempest(target='ctl01',
                                           pattern=settings.PATTERN)
            openstack_deployed.download_tempest_report(stored_node='ctl01')

        expected_service_list = ['monitoring_server',
                                 'monitoring_remote_agent',
                                 'dashboard_grafana',
                                 'monitoring_alertmanager',
                                 'monitoring_remote_collector',
                                 'monitoring_pushgateway']
        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        prometheus_relay_enabled = salt_actions.get_pillar(
            tgt=mon_nodes[0],
            pillar="prometheus:relay:enabled")[0]
        if not prometheus_relay_enabled:
            # InfluxDB is used if prometheus relay service is not installed
            expected_service_list.append('monitoring_remote_storage_adapter')
        show_step(6)
        stacklight_deployed.check_docker_services(mon_nodes,
                                                  expected_service_list)
        # Run SL component tetsts
        if settings.RUN_SL_TESTS:
            show_step(7)
            stacklight_deployed.run_sl_functional_tests(
                'ctl01',
                '/root/stacklight-pytest/stacklight_tests/',
                'tests/prometheus',
                'test_alerts.py')
            show_step(8)
            # Download report
            stacklight_deployed.download_sl_test_report(
                'ctl01',
                '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.extract(container_system='docker', extract_from='conformance',
                         files_to_extract=['report'])
    @pytest.mark.merge_xunit(path='/root/report',
                             output='/root/conformance_result.xml')
    @pytest.mark.grab_k8s_results(name=['k8s_conformance.log',
                                        'conformance_result.xml'])
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_install_opencontrail4_k8s(self, config, show_step,
                                       k8s_deployed, k8s_logs):
        """Test for deploying MCP environment with k8s and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Run conformance if need

        """

        if config.k8s.k8s_conformance_run:
            show_step(5)
            k8s_deployed.run_conformance(raise_on_err=False)
        LOG.info("*************** DONE **************")

    @pytest.mark.extract(container_system='docker', extract_from='conformance',
                         files_to_extract=['report'])
    @pytest.mark.merge_xunit(path='/root/report',
                             output='/root/conformance_result.xml')
    @pytest.mark.grab_k8s_results(name=['k8s_conformance.log',
                                        'conformance_result.xml'])
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_install_opencontrail4_k8s_lma(self, config, show_step,
                                           k8s_deployed,
                                           stacklight_deployed,
                                           k8s_logs):
        """Test for deploying MCP environment with k8s and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Check targets
            6. Check docker services
            7. Run SL tests
            8. Download SL report
            9. Run conformance if need
        """
        # Run SL component tetsts
        if settings.RUN_SL_TESTS:
            show_step(7)
            stacklight_deployed.run_sl_functional_tests(
                'cfg01',
                '/root/stacklight-pytest/stacklight_tests/',
                'tests/prometheus',
                'test_alerts.py')
            show_step(8)
            # Download report
            stacklight_deployed.download_sl_test_report(
                'cfg01',
                '/root/stacklight-pytest/stacklight_tests/report.xml')

        if config.k8s.k8s_conformance_run:
            show_step(9)
            k8s_deployed.run_conformance(raise_on_err=False)
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_contrail4_k8s_pipeline_deploy(self, show_step, underlay,
                                           config, salt_deployed):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts.
            2. Setup controller nodes
            3. Setup compute nodes
            4. Deploy CICD via pipelines
            5. Deploy k8s via cicd pipelines
        """
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        cfg_node = [node for node in nodes
                    if str(node).startswith('cfg')][0]
        salt_api = salt_deployed.get_pillar(
            cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)
        cfg_ip_pillar = salt_deployed.get_pillar(
            cfg_node, '_param:salt_master_host')
        cfg_ip = cfg_ip_pillar[0].get(cfg_node)
        jenkins = JenkinsClient(
            host='http://{}:8081'.format(cfg_ip),
            username='admin',
            password='r00tme')

        # Creating param list for openstack deploy
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        params['STACK_INSTALL'] = 'core,kvm,cicd'
        show_step(4)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy cicd was failed"

        # Changing param for cicd deploy
        cicd_node = [node for node in nodes
                     if str(node).startswith('cid01')][0]

        jenkins_passwd_pillar = salt_deployed.get_pillar(
            cicd_node, 'jenkins:client:master:password')

        jenkins_passwd = jenkins_passwd_pillar[0].get(cicd_node)

        cicd_ip_pillar = salt_deployed.get_pillar(
            cicd_node, 'jenkins:client:master:host')

        cicd_ip = cicd_ip_pillar[0].get(cicd_node)

        jenkins = JenkinsClient(
            host='http://{}:8081'.format(cicd_ip),
            username='admin',
            password=jenkins_passwd)

        params['STACK_INSTALL'] = 'k8s,contrail'
        show_step(5)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy kubernetes was failed"

    @pytest.mark.fail_snapshot
    def test_contrail4_os_pipeline_deploy(self, show_step, underlay,
                                          config, salt_deployed):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts.
            2. Setup controller nodes
            3. Setup compute nodes
            4. Deploy openstack via pipelines
            5. Deploy CICD via pipelines
        """
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        cfg_node = [node for node in nodes
                    if str(node).startswith('cfg')][0]
        salt_api = salt_deployed.get_pillar(
            cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)
        cfg_ip_pillar = salt_deployed.get_pillar(
            cfg_node, '_param:salt_master_host')
        cfg_ip = cfg_ip_pillar[0].get(cfg_node)

        jenkins = JenkinsClient(
            host='http://{}:8081'.format(cfg_ip),
            username='admin',
            password='r00tme')

        # Creating param list for openstack deploy
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        params['STACK_INSTALL'] = 'core,kvm,cicd'
        show_step(4)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy cicd was failed"

        cicd_node = [node for node in nodes
                     if str(node).startswith('cid01')][0]

        jenkins_passwd_pillar = salt_deployed.get_pillar(
            cicd_node, 'jenkins:client:master:password')

        jenkins_passwd = jenkins_passwd_pillar[0].get(cicd_node)

        cicd_ip_pillar = salt_deployed.get_pillar(
            cicd_node, 'jenkins:client:master:host')

        cicd_ip = cicd_ip_pillar[0].get(cicd_node)

        jenkins = JenkinsClient(
            host='http://{}:8081'.format(cicd_ip),
            username='admin',
            password=jenkins_passwd)

        params['STACK_INSTALL'] = 'openstack,contrail'
        show_step(5)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy openstack was failed"
