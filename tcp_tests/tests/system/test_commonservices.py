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
#from tcp_tests import settings

LOG = logger.logger


@pytest.mark.deploy
class TestCommonservices(object):
    """Test class for testing OpenContrail on a TCP lab"""

    @pytest.mark.fail_snapshot
    def test_commonservices(self, config, common_services_deployed,
                            show_step):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Prepare contrail-tests on ctl01 node
        """

        salt_api = \
            salt_deployed.get_pillar(cfg_node, '_param:jenkins_salt_api_url')
        salt_api = salt_api[0].get(cfg_node)

        jenkins = JenkinsClient(
            host='http://172.16.49.66:8081',
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
        
        LOG.info("*************** DONE **************")

        # opencontrail.prepare_tests(
        #     config.opencontrail.opencontrail_prepare_tests_steps_path)

        # opencontrail.run_tests(
        #     tags=config.opencontrail.opencontrail_tags,
        #     features=config.opencontrail.opencontrail_features)
