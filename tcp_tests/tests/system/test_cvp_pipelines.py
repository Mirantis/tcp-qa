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
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestCvpPipelines(object):
    """Test class for running Cloud Validation Pipelines

    Requires environment variables:
      ENV_NAME
      LAB_CONFIG_NAME
      TESTS_CONFIGS
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_cvp_func
    def test_run_cvp_func(self, salt_actions, show_step, _):
        """Runner for Pipeline CVP - Functional tests

        Scenario:
            1. Run job cvp-func
            2. Get passed stages from cvp-func
        """
        salt = salt_actions
        show_step(1)

        tgt = 'I@docker:client:stack:jenkins and cid01*'
        jenkins_host = salt.get_pillar(
            tgt=tgt, pillar="jenkins:client:master:host")[0]
        jenkins_port = salt.get_pillar(
            tgt=tgt, pillar="jenkins:client:master:port")[0]
        jenkins_url = 'http://{0}:{1}'.format(jenkins_host, jenkins_port)
        jenkins_user = salt.get_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")[0]
        jenkins_pass = salt.get_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")[0]
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        job_name = 'cvp-func'
        job_parameters = {
            'TARGET_NODE': 'gtw01*',
        }
        run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters,
            job_output_prefix='[ cvp-func/{build_number}:platform {time} ] ')

        #(build_description, stages) = get_jenkins_job_stages.get_deployment_result(opts)
        #print(build_description)
        #print('\n'.join(stages))

        