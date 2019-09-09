import pytest

from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class TestBackupRestoreGalera(object):
    """
    Created by https://mirantis.jira.com/browse/PROD-32674
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_galera_backup_restore
    def test_backup_restore_galera(self, drivetrain_actions,
                                   show_step, _):
        """Execute backup/restore for galera

        Scenario:
            1. Run job galera_backup_database
            2. Run tests with cvp-sanity job
            3. Run tests with cvp-tempest job
            4. Run job galera_verify_restore
            5. If jobs are passed then start tests with cvp-sanity job
            6. Run tests with cvp-tempest job
        """
        dt = drivetrain_actions

        # ################## Run backup job #########################
        show_step(1)
        job_name = 'galera_backup_database'
        job_parameters = {
            'ASK_CONFIRMATION': False
        }
        backup_galera_pipeline = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)

        assert backup_galera_pipeline == 'SUCCESS'

        # ######################## Run CPV ###########################
        show_step(2)
        job_name = 'cvp-sanity'
        job_cvp_sanity_parameters = {
            'EXTRA_PARAMS': '''

                envs:
                  - skipped_packages='{},{},{},{},{},{}'
                  - skipped_modules='xunitmerge,setuptools'
                  - skipped_services='docker,containerd'
                  - ntp_skipped_nodes=''
                  - tests_set=-k "not {} and not {} and not {}"
            '''.format('python-setuptools', 'python-pkg-resources',
                       'xunitmerge', 'python-gnocchiclient',
                       'python-ujson', 'python-octaviaclient',
                       'test_ceph_status', 'test_prometheus_alert_count',
                       'test_uncommited_changes')
        }
        run_cvp_sanity = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_cvp_sanity_parameters)

        assert run_cvp_sanity == 'SUCCESS'

        # ######################## Run Tempest ###########################
        show_step(3)
        job_name = 'cvp-tempest'
        job_parameters = {
             'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        }
        run_cvp_tempest = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)

        assert run_cvp_tempest == 'SUCCESS'
        # ######################## Run Restore ###########################
        show_step(4)
        job_name = 'galera_verify_restore'
        job_parameters = {
             'RESTORE_TYPE': 'ONLY_RESTORE',
             'ASK_CONFIRMATION': False
        }
        run_galera_verify_restore = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)

        assert run_galera_verify_restore == 'SUCCESS'
        # ######################## Run CPV ###########################
        show_step(5)
        job_name = 'cvp-sanity'
        run_cvp_sanity = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_cvp_sanity_parameters)

        assert run_cvp_sanity == 'SUCCESS'
        # ######################## Run Tempest ###########################
        show_step(6)
        job_name = 'cvp-tempest'
        job_parameters = {
             'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        }
        run_cvp_tempest = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)

        assert run_cvp_tempest == 'SUCCESS'
