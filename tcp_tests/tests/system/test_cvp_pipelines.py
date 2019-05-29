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

import jenkins
import pytest
import os

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages
from tcp_tests.utils import get_jenkins_job_artifact

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
            4. Download XML report from the job
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

        try:
            maas_minion_id = salt.get_single_pillar(
                tgt='I@maas:cluster or I@maas:region',
                pillar="__reclass__:nodename")
            ntp_skipped_nodes = 'ntp_skipped_nodes={0}'.format(maas_minion_id)
        except LookupError:
            ntp_skipped_nodes = ''

        job_name = 'cvp-sanity'
        skipped_packages = ("python-setuptools,"
                            "python-pkg-resources,xunitmerge,"
                            "python-gnocchiclient, "
                            "python-ujson,python-octaviaclient")

        job_parameters = {
            'EXTRA_PARAMS': (
                """
                envs:
                  - skipped_packages='{0}'
                  - skipped_modules='xunitmerge,setuptools'
                  - skipped_services='docker,containerd'
                  - skipped_nodes='{1}'"""
                .format(skipped_packages, ntp_skipped_nodes)),
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
        LOG.info('Job {0} result: {1}'.format(job_name,
                                              cvp_func_sanity_result))
        # Download XML report
        show_step(4)
        destination_name = os.path.join(settings.LOGS_DIR,
                                        "cvp_sanity_results.xml")
        # Do not fail the test case when the job is failed, but
        # artifact with the XML report is present in the job.
        try:
            get_jenkins_job_artifact.download_artifact(
                host=jenkins_url,
                username=jenkins_user,
                password=jenkins_pass,
                job_name=job_name,
                build_number='lastBuild',
                artifact_path='validation_artifacts/cvp-sanity_report.xml',
                destination_name=destination_name)
        except jenkins.NotFoundException:
            raise jenkins.NotFoundException("{0}\n{1}".format(
                description, '\n'.join(stages)))

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
            4. Download XML report from the job
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
        LOG.info('Job {0} result: {1}'.format(job_name,
                                              cvp_stacklight_result))
        # Download XML report
        show_step(4)
        destination_name = os.path.join(settings.LOGS_DIR,
                                        "stacklight_report.xml")
        # Do not fail the test case when the job is failed, but
        # artifact with the XML report is present in the job.
        try:
            get_jenkins_job_artifact.download_artifact(
                host=jenkins_url,
                username=jenkins_user,
                password=jenkins_pass,
                job_name=job_name,
                build_number='lastBuild',
                artifact_path='validation_artifacts/cvp-stacklight_report.xml',
                destination_name=destination_name)
        except jenkins.NotFoundException:
            raise jenkins.NotFoundException("{0}\n{1}".format(
                description, '\n'.join(stages)))

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_cvp_tempest
    def test_run_cvp_tempest(self, salt_actions, show_step, _):
        """Runner for Pipeline CVP - Tempest

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job cvp-tempest
            3. Get passed stages from cvp-tempest
            4. Download XML report from the job
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

        os_version = salt.get_single_pillar(
            tgt='I@salt:master', pillar="_param:openstack_version")

        job_name = 'cvp-tempest'
        job_parameters = {
            'EXTRA_PARAMS': (
                """
                ---
                  DEBUG_MODE: false
                  GENERATE_CONFIG: true
                  TARGET_NODE: 'cid01*'
                  TEST_IMAGE: 'docker-prod-virtual.docker.mirantis.net/mirantis/cicd/ci-tempest:{0}'
                  report_prefix: 'cvp_'"""
                .format(os_version)),
        }

        show_step(2)
        cvp_tempest_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters,
            job_output_prefix='[cvp-tempest/{build_number}:platform {time}]'
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
        LOG.info('Job {0} result: {1}'.format(job_name,
                                              cvp_tempest_result))
        # Download XML report
        show_step(4)
        destination_name = os.path.join(settings.LOGS_DIR,
                                        "tempest_report.xml")
        # Do not fail the test case when the job is failed, but
        # artifact with the XML report is present in the job.
        try:
            get_jenkins_job_artifact.download_artifact(
                host=jenkins_url,
                username=jenkins_user,
                password=jenkins_pass,
                job_name=job_name,
                build_number='lastBuild',
                artifact_path='validation_artifacts/cvp-tempest_report.xml',
                destination_name=destination_name)
        except jenkins.NotFoundException:
            raise jenkins.NotFoundException("{0}\n{1}".format(
                description, '\n'.join(stages)))
