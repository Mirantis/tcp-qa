import pytest

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestUpdateMcpCluster(object):
    """
    Following the steps in
    https://docs.mirantis.com/mcp/q4-18/mcp-operations-guide/update-upgrade/minor-update.html#minor-update
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_drivetrain(self, salt_actions, show_step, _):
        """
        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job git-mirror-downstream-mk-pipelines
            3. Run job git-mirror-downstream-pipeline-library
            4. If jobs are passed start 'Deploy - upgrade MCP Drivetrain' job
        """
        salt = salt_actions

        # #################### Login Jenkins on cid01 node ###################
        show_step(1)

        jenkins_url = salt.login_cluster_jenkins().get('url')
        jenkins_user = salt.login_cluster_jenkins().get('user')
        jenkins_pass = salt.login_cluster_jenkins().get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        # FIXME: workaround for PROD-32751
        salt.cmd_run("cfg01*", "cd /srv/salt/reclass; git add -u && \
                        git commit --allow-empty -m 'Cluster model update'")

        # ################### Downstream mk-pipelines #########################
        show_step(2)
        job_name = 'git-mirror-downstream-mk-pipelines'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        update_pipelines = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_pipelines == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

        # ################### Downstream pipeline-library ####################
        show_step(3)
        job_name = 'git-mirror-downstream-pipeline-library'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        update_pipeline_library = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_pipeline_library == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

        # ################### Start 'Deploy - upgrade MCP Drivetrain' job #####
        show_step(4)

        jenkins_build_timeout = 3600
        job_name = 'upgrade-mcp-release'
        job_parameters = {
            'MK_PIPELINES_REFSPEC': 'release/proposed/2019.2.0',
            'TARGET_MCP_VERSION': '2019.2.0'
        }
        update_drivetrain = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=True,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_drivetrain == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

    @pytest.mark.run_mcp_update
    def test_update_gluster(self):
        pass
