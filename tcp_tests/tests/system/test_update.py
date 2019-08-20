import jenkins
import pytest
import os

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages
from tcp_tests.utils import get_jenkins_job_artifact

LOG = logger.logger


class TestUpdateDrivetrain(object):
    """
    gfa
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_cvp_func_smoke
    def test_update_job(self, salt_actions, show_step, _):
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
        jenkins_protocol = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:proto")
        jenkins_url = '{0}://{1}:{2}'.format(jenkins_protocol,
                                             jenkins_host,
                                             jenkins_port)
        jenkins_user = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")
        jenkins_pass = salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        job_name = 'git-mirror-downstream-pipeline-library'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        show_step(2)
        updateDT_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters,
            job_output_prefix='[ git-mirror-downstream-pipeline-library/{build_number}:platform {time} ] ')

        show_step(3)
        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        salt.cmd_run("cfg01*", "echo 'hello' >> /root/1.txt; cat /root/1.txt")
        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert True
