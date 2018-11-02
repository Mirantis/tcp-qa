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
class TestPipeline(object):
    """Test class for testing deploy via Pipelines"""

    @pytest.mark.fail_snapshot
    def test_pipeline(self, show_step, underlay,
                      salt_deployed, tempest_actions):
        """Deploy bm via pipeline

        Scenario:
            1. Prepare salt on hosts.
            2. Connect to jenkins on cfg01 node
            3. Run deploy on cfg01 node
            4. Connect to jenkins on cid node
            5. Run deploy on cid node
        """
        show_step(1)
        nodes = underlay.node_names()
        LOG.info("Nodes - {}".format(nodes))
        show_step(2)

        cfg_ip = salt_deployed.host
        salt_api = 'http://{}:6969'.format(cfg_ip)
        jenkins = JenkinsClient(
            host='http://{}:8081'.format(cfg_ip),
            username='admin',
            password='r00tme')

        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        params['STACK_INSTALL'] = 'core,kvm,cicd'

        show_step(3)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy openstack was failed"

        show_step(4)

        jenkins_target = 'I@docker:client:stack:jenkins'
        jenkins_user = salt_deployed.get_pillar(
            jenkins_target, 'jenkins:client:master:username')
        jenkins_passwd = salt_deployed.get_pillar(
            jenkins_target, 'jenkins:client:master:password')
        jenkins_host = salt_deployed.get_pillar(
            jenkins_target, 'jenkins:client:master:host')
        jenkins_port = salt_deployed.get_pillar(
            jenkins_target, 'jenkins:client:master:port')

        cicd_ip = cicd_ip_pillar[0].get(cicd_node)

        jenkins = JenkinsClient(
            host='http://{host}:{port}'.format(host=jenkins_host,
                                               port=jenkins_port),
            username=jenkins_user, password=jenkins_passwd)

        params['STACK_INSTALL'] = 'ovs,openstack'
        show_step(5)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy openstack was failed"

        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()
        LOG.info("*************** DONE **************")
