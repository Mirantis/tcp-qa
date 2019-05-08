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
    @pytest.mark.run_cvp_func_smoke
    def test_run_cvp_func_smoke(self, salt_actions, show_step, _):
        """Runner for Pipeline CVP - Functional tests

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job cvp-func
            3. Get passed stages from cvp-func
        """
        salt = salt_actions
        show_step(1)

        tgt = 'I@docker:client:stack:jenkins and cid01*'
        jenkins_host = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:host")
        jenkins_port = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:port")
        jenkins_url = 'http://{0}:{1}'.format(jenkins_host, jenkins_port)
        jenkins_user = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")
        jenkins_pass = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        job_name = 'cvp-func'
        job_parameters = {
            'TARGET_NODE': 'gtw01*',
            'TEMPEST_ENDPOINT_TYPE': 'internalURL',
            'TEMPEST_TEST_PATTERN': 'set=smoke',
        }
        show_step(2)
        cvp_func_smoke_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters,
            job_output_prefix='[ cvp-func/{build_number}:platform {time} ] ')

        show_step(3)
        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert cvp_func_smoke_result == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_cvp_func_sanity
    def test_run_cvp_func_sanity(self, salt_actions, show_step, _):
        """Runner for Pipeline CVP - Functional tests

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job cvp-sanity
            3. Get passed stages from cvp-sanity
        """
        salt = salt_actions
        show_step(1)

        tgt = 'I@docker:client:stack:jenkins and cid01*'
        jenkins_host = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:host")
        jenkins_port = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:port")
        jenkins_url = 'http://{0}:{1}'.format(jenkins_host, jenkins_port)
        jenkins_user = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")
        jenkins_pass = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        maas_minion_id = salt.get_single_pillar(
            tgt='I@maas:cluster:enabled:True or I@maas:region:enabled:True',
            pillar="__reclass__:nodename")

        job_name = 'cvp-sanity'
        job_parameters = {
            'TEST_SET': '/var/lib/cvp-sanity/cvp_checks/tests/',
            'TESTS_SETTINGS': (
                'drivetrain_version={0};ntp_skipped_nodes={1}'
                .format(settings.MCP_VERSION, maas_minion_id)),
        }

        show_step(2)
        cvp_func_sanity_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters,
            job_output_prefix='[ cvp-func/{build_number}:platform {time} ] ')

        show_step(3)
        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert cvp_func_sanity_result == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_cvp_ha_smoke
    def test_run_cvp_ha_smoke(self, underlay_actions, salt_actions,
                              show_step, _):
        """Runner for Pipeline CVP - HA tests

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job cvp-ha with tempest set=smoke
            3. Get passed stages from cvp-ha
        """
        salt = salt_actions
        show_step(1)

        tgt = 'I@docker:client:stack:jenkins and cid01*'
        jenkins_host = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:host")
        jenkins_port = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:port")
        jenkins_url = 'http://{0}:{1}'.format(jenkins_host, jenkins_port)
        jenkins_user = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")
        jenkins_pass = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        tempest_target_node = salt.get_single_pillar(
            tgt='cfg01*',
            pillar="runtest:tempest:test_target")

        job_name = 'cvp-ha'
        job_parameters = {
            'TEMPEST_TARGET_NODE': tempest_target_node,
            'TEMPEST_TEST_PATTERN': 'set=smoke',
        }

        show_step(2)
        cvp_ha_smoke_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters,
            job_output_prefix='[ cvp-ha/{build_number} {time} ] ')

        show_step(3)
        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert cvp_ha_smoke_result == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_stacklight
    def test_run_cvp_stacklight(self, salt_actions, show_step, _):
        """Runner for Pipeline CVP - Stacklight

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job cvp-stacklight
            3. Get passed stages from cvp-stacklight
        """
        salt = salt_actions
        show_step(1)

        tgt = 'I@docker:client:stack:jenkins and cid01*'
        jenkins_host = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:host")
        jenkins_port = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:port")
        jenkins_url = 'http://{0}:{1}'.format(jenkins_host, jenkins_port)
        jenkins_user = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")
        jenkins_pass = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        job_name = 'cvp-stacklight'

        show_step(2)
        cvp_stacklight_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters={},
            job_output_prefix='[cvp-stacklight/{build_number}:platform {time}]'
        )

        show_step(3)
        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert cvp_stacklight_result == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))
