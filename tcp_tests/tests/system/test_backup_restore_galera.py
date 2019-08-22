import pytest

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestBackupRestoreGalera(object):
    """
    Created by https://mirantis.jira.com/browse/PROD-32674
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_galera_backup_restore
    def test_backup_restore_galera(self, salt_actions, show_step, _):
        """Execute backup/restore for galera

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run tests with cvp-tempest job
            3. Run job galera_backup_database
            4. Run job galera_verify_restore
            5. If jobs are passed then start tests with cvp-tempest job
        """
        salt = salt_actions

        # ################### Login Jenkins on cid01 node ###################
        show_step(1)

        jenkins_url = salt.login_cluster_jenkins().get('url')
        jenkins_user = salt.login_cluster_jenkins().get('user')
        jenkins_pass = salt.login_cluster_jenkins().get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        # ################### Run backup job #########################
        # show_step(2)
        # job_name = 'galera_backup_database'
        # job_parameters = {
        #     'ASK_CONFIRMATION': False
        # }
        # backup_galera_pipeline = run_jenkins_job.run_job(
        #     host=jenkins_url,
        #     username=jenkins_user,
        #     password=jenkins_pass,
        #     start_timeout=jenkins_start_timeout,
        #     build_timeout=jenkins_build_timeout,
        #     verbose=False,
        #     job_name=job_name,
        #     job_parameters=job_parameters)

        # (description, stages) = get_jenkins_job_stages.get_deployment_result(
        #     host=jenkins_url,
        #     username=jenkins_user,
        #     password=jenkins_pass,
        #     job_name=job_name,
        #     build_number='lastBuild')

        # LOG.info(description)
        # LOG.info('\n'.join(stages))

        # assert backup_galera_pipeline == 'SUCCESS', "{0}\n{1}".format(
        #     description, '\n'.join(stages))
        # ######################## Run CPV ###########################
        # show_step(3)
        # job_name = 'cvp-sanity'
        # job_parameters = {}
        # run_cvp_sanity = run_jenkins_job.run_job(
        #     host=jenkins_url,
        #     username=jenkins_user,
        #     password=jenkins_pass,
        #     start_timeout=jenkins_start_timeout,
        #     build_timeout=jenkins_build_timeout,
        #     verbose=False,
        #     job_name=job_name,
        #     job_parameters=job_parameters)

        # (description, stages) = get_jenkins_job_stages.get_deployment_result(
        #     host=jenkins_url,
        #     username=jenkins_user,
        #     password=jenkins_pass,
        #     job_name=job_name,
        #     build_number='lastBuild')

        # LOG.info(description)
        # LOG.info('\n'.join(stages))

        # assert run_cvp_sanity == 'SUCCESS', "{0}\n{1}".format(
        #     description, '\n'.join(stages))
        # ######################## Run Tempest ###########################
        # show_step(4)
        # job_name = 'cvp-tempest'
        # job_parameters = {
        #      'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        # }
        # run_cvp_tempest = run_jenkins_job.run_job(
        #     host=jenkins_url,
        #     username=jenkins_user,
        #     password=jenkins_pass,
        #     start_timeout=jenkins_start_timeout,
        #     build_timeout=jenkins_build_timeout,
        #     verbose=False,
        #     job_name=job_name,
        #     job_parameters=job_parameters)

        # (description, stages) = get_jenkins_job_stages.get_deployment_result(
        #     host=jenkins_url,
        #     username=jenkins_user,
        #     password=jenkins_pass,
        #     job_name=job_name,
        #     build_number='lastBuild')

        # LOG.info(description)
        # LOG.info('\n'.join(stages))

        # assert run_cvp_tempest == 'SUCCESS', "{0}\n{1}".format(
        #     description, '\n'.join(stages))
        # ######################## Run Restore ###########################
        show_step(5)
        job_name = 'galera_verify_restore'
        job_parameters = {
             'RESTORE_TYPE': 'ONLY_RESTORE',
             'ASK_CONFIRMATION': False
        }
        run_galera_verify_restore = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=False,
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

        assert run_galera_verify_restore == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))
        # ######################## Run Tempest ###########################
        show_step(6)
        job_name = 'cvp-tempest'
        job_parameters = {
             'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        }
        run_cvp_tempest = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=False,
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

        assert run_cvp_tempest == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))
