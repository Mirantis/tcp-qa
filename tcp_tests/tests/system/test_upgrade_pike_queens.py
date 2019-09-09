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
import json

from tcp_tests import logger
# from tcp_tests.managers.jenkins.client import JenkinsClient
# from tcp_tests import settings

# from tcp_tests import managers

LOG = logger.logger


class TestUpdatePikeToQueens(object):
    """
    Created by https://mirantis.jira.com/browse/PROD-32683
    """
    @pytest.mark.day1_underlay
    def test_upgrade_pike_queens(self,
                                 show_step,
                                 underlay_actions,
                                 drivetrain_actions,
                                 reclass_actions,
                                 salt_actions):
        """Execute upgrade from Pike to Queens

        Scenario:
            1. Perform the pre-upgrade activities
            2. Upgrade RabbitMQ
            3. Upgrade control VMs
            4. Upgrade gatewey nodes
            5. Upgrade compute nodes
            6. Upgrade galera
            7. Perform the post-upgrade activities
            8. If jobs are passed then start tests with cvp-sanity job
            9. Run tests with cvp-tempest job
        """
        cfg_node = underlay_actions.get_target_node_names(target='cfg')[0]
        LOG.info('cfg node is {}'.format(cfg_node))
        verbose = True
        dt = drivetrain_actions
        # ############ Perform the pre-upgrade activities ###########
        show_step(1)
        # deploy-upgrade-control
        # LOG.info('Execute db online_data_migrations')
        # for i in ['nova-manage', 'cinder-manage']:
        #     ret = salt_actions.cmd_run('ctl01*',
        #         '{} db online_data_migrations'.format(i))
        #     LOG.debug(ret)
        # LOG.info('Apply state keystone.client.os_client_config')
        # ret = salt_actions.run_state('I@heat:server', 'state.apply',
        #                      'keystone.client.os_client_config')
        # LOG.debug(ret)
        # LOG.info('Get upgarded components')
        # ret = underlay_actions.check_call(
        #     node_name=cfg_node, verbose=verbose,
        #     cmd='salt-call -l error config.get '
        #         'orchestration:upgrade:application'
        #      ' --out=json')
        # LOG.info(ret)
        # ########## Upgrade RabbitMQ #########
        show_step(2)
        LOG.info('Upgrade RabbitMQ')
        # job_name = 'deploy-upgrade-rabbitmq'
        # job_parameters = {
        #     'INTERACTIVE': False,
        #     'OS_DIST_UPGRADE': False,
        #     'OS_UPGRADE': False
        # }
        # update_rabbit = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert update_rabbit == 'SUCCESS'
        # ########## Upgrade control VMs #########
        show_step(3)
        LOG.info('Upgrade control VMs')
        # job_name = 'deploy-upgrade-control'
        # job_parameters = {
        #     'INTERACTIVE': False,
        #     'OS_DIST_UPGRADE': False,
        #     'OS_UPGRADE': False
        # }
        # update_control_vms = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert update_control_vms == 'SUCCESS'
        # ########## Upgrade gatewey nodes  ###########
        show_step(4)
        LOG.info('Upgrade gateway')
        job_name = 'deploy-upgrade-ovs-gateway'
        # job_parameters = {
        #     'INTERACTIVE': False,
        #     'OS_DIST_UPGRADE': False,
        #     'OS_UPGRADE': False
        # }
        # update_gateway = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert update_gateway == 'SUCCESS'
        # ############ Upgrade compute nodes  ############
        show_step(5)
        LOG.info('Upgrade compute nodes')
        # job_name = 'deploy-upgrade-compute'
        # job_parameters = {
        #     'INTERACTIVE': False,
        #     'OS_DIST_UPGRADE': False,
        #     'OS_UPGRADE': False
        # }
        # update_computes = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert update_computes == 'SUCCESS'
        # ############ Upgrade galera  ############
        show_step(6)
        LOG.info('Upgrade galera')
        # job_name = 'deploy-upgrade-galera'
        # job_parameters = {
        #     'INTERACTIVE': False,
        #     'OS_DIST_UPGRADE': False,
        #     'OS_UPGRADE': False
        # }
        # update_galera = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert update_galera == 'SUCCESS'
        # ############ Perform the post-upgrade activities ##########
        show_step(7)
        LOG.info('Add parameters._param.openstack_upgrade_enabled false to '
                 'cluster/*/infa/init.yml')
        reclass_actions.add_bool_key(
            'parameters._param.openstack_upgrade_enabled',
            'false',
            'cluster/*/infa/init.yml')
        LOG.info('Perform refresh_pillar')
        ret = salt_actions.run_state("*", "saltutil.refresh_pillar")
        ret = underlay_actions.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="salt 'cfg01*' config.get orchestration:upgrade:applications --out=json")
        full_nodes = json.loads(ret)
        LOG.info(ret)
        # ######################## Run CPV ##########################
        show_step(8)
        # job_name = 'cvp-sanity'
        # job_parameters = {
        #     'EXTRA_PARAMS': '''
        #         envs:
        #           - skipped_packages='{},{},{},{},{},{}'
        #           - skipped_modules='xunitmerge,setuptools'
        #           - skipped_services='docker,containerd'
        #           - ntp_skipped_nodes=''
        #           - tests_set=-k "not {} and not {} and not {}"
        #     '''.format('python-setuptools', 'python-pkg-resources',
        #                'xunitmerge', 'python-gnocchiclient',
        #                'python-ujson', 'python-octaviaclient',
        #                'test_ceph_status', 'test_prometheus_alert_count',
        #                'test_uncommited_changes')
        # }
        # run_cvp_sanity = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert run_cvp_sanity == 'SUCCESS'
        # ######################## Run Tempest #######################
        show_step(9)
        # job_name = 'cvp-tempest'
        # job_parameters = {
        #      'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        # }
        # run_cvp_tempest = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)
        # assert run_cvp_tempest == 'SUCCESS'
