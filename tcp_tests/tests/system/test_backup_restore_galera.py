import pytest

from devops.helpers.proc_enums import ExitCodes
from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class TestBackupRestoreGalera(object):
    """
    Created by https://mirantis.jira.com/browse/PROD-32674
    """
    @pytest.fixture()
    def handle_restore_params(self, reclass_actions):
        reclass_actions.add_key(
            'parameters.xtrabackup.client.restore_full_latest',
            '1',
            'cluster/*/openstack/database/init.yml')
        reclass_actions.add_bool_key(
            'parameters.xtrabackup.client.enabled',
            'True',
            'cluster/*/openstack/database/init.yml')
        reclass_actions.add_key(
            'parameters.xtrabackup.client.restore_from',
            'remote',
            'cluster/*/openstack/database/init.yml')
        yield
        reclass_actions.delete_key(
            'parameters.xtrabackup.client.restore_full_latest',
            'cluster/*/openstack/database/init.yml')
        reclass_actions.delete_key(
            'parameters.xtrabackup.client.enabled',
            'cluster/*/openstack/database/init.yml')
        reclass_actions.delete_key(
            'parameters.xtrabackup.client.restore_from',
            'cluster/*/openstack/database/init.yml')

    def _get_cfg_fqn(self, salt):
        salt_master = salt.local("I@salt:master", "network.get_fqdn")
        return salt_master['return'][0].keys()[0]

    def _perform_action_on_flavor(self, underlay_actions,
                                  name, action, cfg_node):
        xxx = underlay_actions.check_call(
            'source /root/keystonercv3 && '
            'openstack flavor {} {}'.format(action, name),
            node_name=cfg_node)
        LOG.info(xxx)

    def create_flavor(self, underlay_actions, name, cfg_node):
        self._perform_action_on_flavor(underlay_actions, name, 'create', cfg_node)

    def delete_flavor(self, underlay_actions, name, cfg_node):
        self._perform_action_on_flavor(underlay_actions, name, 'delete', cfg_node)

    def is_flavor_restored(self, underlay_actions, name, cfg_node):
        get_by_name = underlay_actions.check_call(
            'source /root/keystonercv3 && ' +
            'openstack flavor show {}'.format(name),
            node_name=cfg_node,
            raise_on_err=False,
            expected=[ExitCodes.EX_OK, ExitCodes.EX_ERROR]
        )
        # result = result.join(get_by_name)
        LOG.info(get_by_name)
        LOG.info('!!!!!!!!!!!!!!!')
        # LOG.info(get_by_name['stderr'][0].startswith('No flavor'))
        return len(get_by_name['stderr']) == 0
        # LOG.info(get_by_name['stderr'] == '')
        # return not get_by_name['stderr'].startswith('No flavor')

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_galera_backup_restore
    def test_backup_restore_galera(self, salt_actions, drivetrain_actions,
                                   show_step, underlay_actions,
                                   handle_restore_params,  _):
        """Execute backup/restore for galera

        Scenario:
            1. Create flavor to be backuped
            2. Run job galera_backup_database
            3. Run tests with cvp-sanity job
            4. Run tests with cvp-tempest job
            5. Create flavor not to be restored
            6. Run job galera_verify_restore
            7. If jobs are passed then start tests with cvp-sanity job
            8. Run tests with cvp-tempest job
        """
        dt = drivetrain_actions
        salt = salt_actions

        show_step(1)
        cfg_node = self._get_cfg_fqn(salt)
        fixture_flavor1 = 'test1'
        fixture_flavor2 = 'test2'
        self.create_flavor(underlay_actions, fixture_flavor1, cfg_node)
        # # ################## Run backup job #########################
        # show_step(2)
        # job_name = 'galera_backup_database'
        # job_parameters = {
        #     'ASK_CONFIRMATION': False
        # }
        # backup_galera_pipeline = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        #
        # assert backup_galera_pipeline == 'SUCCESS'
        #
        # # ######################## Run CPV ###########################
        # show_step(3)
        # # job_name = 'cvp-sanity'
        # # job_cvp_sanity_parameters = {
        # #     'EXTRA_PARAMS': '''
        # #
        # #         envs:
        # #           - skipped_packages='{},{},{},{},{},{}'
        # #           - skipped_modules='xunitmerge,setuptools'
        # #           - skipped_services='docker,containerd'
        # #           - ntp_skipped_nodes=''
        # #           - tests_set=-k "not {} and not {} and not {}"
        # #     '''.format('python-setuptools', 'python-pkg-resources',
        # #                'xunitmerge', 'python-gnocchiclient',
        # #                'python-ujson', 'python-octaviaclient',
        # #                'test_ceph_status', 'test_prometheus_alert_count',
        # #                'test_uncommited_changes')
        # # }
        # # run_cvp_sanity = dt.start_job_on_cid_jenkins(
        # #     job_name=job_name,
        # #     job_parameters=job_cvp_sanity_parameters)
        # #
        # # assert run_cvp_sanity == 'SUCCESS'
        #
        # # ######################## Run Tempest ###########################
        # show_step(4)
        # job_name = 'cvp-tempest'
        # job_parameters = {
        #      'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        # }
        # # run_cvp_tempest = dt.start_job_on_cid_jenkins(
        # #     job_name=job_name,
        # #     job_parameters=job_parameters)
        #
        # # assert run_cvp_tempest == 'SUCCESS'
        # show_step(5)
        # self.create_flavor(underlay_actions, fixture_flavor2, cfg_node)
        # # ######################## Run Restore ###########################
        # show_step(6)
        # job_name = 'galera_verify_restore'
        # job_parameters = {
        #      'RESTORE_TYPE': 'ONLY_RESTORE',
        #      'ASK_CONFIRMATION': False
        # }
        # run_galera_verify_restore = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        #
        # assert run_galera_verify_restore == 'SUCCESS'
        #
        assert self.is_flavor_restored(underlay_actions, fixture_flavor1, cfg_node)
        assert self.is_flavor_restored(underlay_actions, fixture_flavor2, cfg_node) is False
        # # ######################## Run CPV ###########################
        # show_step(7)
        #
        # # job_name = 'cvp-sanity'
        # # run_cvp_sanity = dt.start_job_on_cid_jenkins(
        # #     job_name=job_name,
        # #     job_parameters=job_cvp_sanity_parameters)
        # #
        # # assert run_cvp_sanity == 'SUCCESS'
        # # ######################## Run Tempest ###########################
        # show_step(8)
        # job_name = 'cvp-tempest'
        # job_parameters = {
        #      'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        # }
        # # run_cvp_tempest = dt.start_job_on_cid_jenkins(
        # #     job_name=job_name,
        # #     job_parameters=job_parameters)
        #
        # # assert run_cvp_tempest == 'SUCCESS'
        self.delete_flavor(underlay_actions, fixture_flavor1, cfg_node)
