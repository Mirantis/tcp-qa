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

LOG = logger.logger


@pytest.mark.deploy
class TestPipeline(object):
    """Test class for testing deploy via Pipelines"""

    @pytest.mark.fail_snapshot
    def test_pipeline(self, show_step, underlay,
                      common_services_deployed, salt_deployed):
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
        cfg_node = 'cfg01.ocata-cicd-contrail.local'
        salt_api = salt_deployed.get_pillar(
            cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)
        jenkins = JenkinsClient(
            host='http://172.16.49.66:8081',
            username='admin',
            password='r00tme')

        # Creating param list for openstack deploy
        params = jenkins.make_defults_params('deploy_openstack')
        params['SALT_MASTER_URL'] = salt_api
        params['STACK_INSTALL'] = 'core,kvm,openstack,contrail'
        show_step(4)
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 4)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy openstack was failed"

        # Changing param for cicd deploy
        show_step(5)
        params['STACK_INSTALL'] = 'cicd'
        build = jenkins.run_build('deploy_openstack', params)
        jenkins.wait_end_of_build(
            name=build[0],
            build_id=build[1],
            timeout=60 * 60 * 2)
        result = jenkins.build_info(name=build[0],
                                    build_id=build[1])['result']
        assert result == 'SUCCESS', "Deploy CICD was failed"

        LOG.info("*************** DONE **************")
