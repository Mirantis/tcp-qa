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


LOG = logger.logger


class TestUpdatePikeToQueens(object):
    """
    Created by https://mirantis.jira.com/browse/PROD-32683
    """
    def execute_pre_post_steps(self, underlay_actions,
                               cfg_node, verbose, type):
        ret = underlay_actions.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="salt 'cfg01*' config.get"
                " orchestration:upgrade:applications --out=json")
        cfg_nodes_list = json.loads(ret['stdout_str'])
        services_for_upgrade = []
        for i in cfg_nodes_list:
            for j in cfg_nodes_list[i]:
                services_for_upgrade.append(j)
        LOG.info(services_for_upgrade)
        list_nodes = underlay_actions.check_call(
            node_name=cfg_node, verbose=verbose,
            cmd="salt-key -l accepted | grep -v cfg01 | "
                "grep -v Accepted")['stdout_str'].splitlines()
        LOG.info(list_nodes)
        for node in list_nodes:
            salt_pillars = underlay_actions.check_call(
                node_name=cfg_node, verbose=verbose,
                cmd="salt {} pillar.items __reclass__:applications"
                    " --out=json".format(node))
            node_app_output = json.loads(salt_pillars['stdout_str'])
            need_output = '__reclass__:applications'
            LOG.info(node_app_output)
            if need_output in node_app_output[node]:
                node_applications = node_app_output[node][need_output]
                LOG.info(node_applications)
                for service in services_for_upgrade:
                    if service in node_applications:
                        underlay_actions.check_call(
                            node_name=cfg_node, verbose=verbose,
                            cmd="salt {} state.apply "
                                "{}.upgrade.{}".format(node, service, type))

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
        # ########## Perform the pre-upgrade activities ##########
        show_step(1)
        LOG.info('Add parameters to '
                 'cluster/*/infa/init.yml')
        reclass_actions.add_bool_key(
            'parameters._param.openstack_upgrade_enabled',
            'true',
            'cluster/heat-cicd-pike-dvr-sl/infa/init.yml')
        LOG.info('Add openstack_version: queens')
        reclass_actions.add_key(
            'parameters._param.openstack_version',
            'queens',
            'cluster/heat-cicd-pike-dvr-sl/infa/init.yml')
        LOG.info('Add openstack_old_version: pike')
        reclass_actions.add_key(
            'parameters._param.openstack_old_version',
            'pike',
            'cluster/heat-cicd-pike-dvr-sl/infa/init.yml')
        LOG.info('Perform refresh_pillar')
        salt_actions.run_state("*", "saltutil.refresh_pillar")
        self.execute_pre_post_steps(underlay_actions, cfg_node,
                                    verbose, 'pre')
        LOG.info('Perform refresh_pillar')
        salt_actions.run_state("*", "saltutil.refresh_pillar")
        # ########## Upgrade RabbitMQ #########
        show_step(2)
        LOG.info('Upgrade RabbitMQ')
        job_name = 'deploy-upgrade-rabbitmq'
        job_parameters = {
            'INTERACTIVE': False,
            'OS_DIST_UPGRADE': False,
            'OS_UPGRADE': False
        }
        update_rabbit = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert update_rabbit == 'SUCCESS'
        # ########## Upgrade control VMs #########
        show_step(3)
        LOG.info('Upgrade control VMs')
        job_name = 'deploy-upgrade-control'
        job_parameters = {
            'INTERACTIVE': False,
            'OS_DIST_UPGRADE': False,
            'OS_UPGRADE': False
        }
        update_control_vms = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert update_control_vms == 'SUCCESS'
        # ########## Upgrade gatewey nodes  ###########
        show_step(4)
        LOG.info('Upgrade gateway')
        job_name = 'deploy-upgrade-ovs-gateway'
        job_parameters = {
            'INTERACTIVE': False,
            'OS_DIST_UPGRADE': False,
            'OS_UPGRADE': False
        }
        update_gateway = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert update_gateway == 'SUCCESS'
        # ############ Upgrade compute nodes  ############
        show_step(5)
        LOG.info('Upgrade compute nodes')
        job_name = 'deploy-upgrade-compute'
        job_parameters = {
            'INTERACTIVE': False,
            'OS_DIST_UPGRADE': False,
            'OS_UPGRADE': False
        }
        update_computes = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert update_computes == 'SUCCESS'
        # ############ Upgrade galera  ############
        show_step(6)
        LOG.info('Upgrade galera')
        job_name = 'deploy-upgrade-galera'
        job_parameters = {
            'INTERACTIVE': False,
            'OS_DIST_UPGRADE': False,
            'OS_UPGRADE': False
        }
        update_galera = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert update_galera == 'SUCCESS'
        # ############ Perform the post-upgrade activities ##########
        show_step(7)
        LOG.info('Add parameters._param.openstack_upgrade_enabled false to '
                 'cluster/heat-cicd-pike-dvr-sl/infa/init.yml')
        reclass_actions.add_bool_key(
            'parameters._param.openstack_upgrade_enabled',
            'false',
            'cluster/heat-cicd-pike-dvr-sl/infa/init.yml')
        LOG.info('Perform refresh_pillar')
        salt_actions.run_state("*", "saltutil.refresh_pillar")
        self.execute_pre_post_steps(underlay_actions, cfg_node,
                                    verbose, 'post')
        LOG.info('Perform refresh_pillar')
        salt_actions.run_state("*", "saltutil.refresh_pillar")
        # ######################## Run CPV ##########################
        show_step(8)
        job_name = 'cvp-sanity'
        job_parameters = {
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
            job_parameters=job_parameters)
        assert run_cvp_sanity == 'SUCCESS'
        # ######################## Run Tempest #######################
        show_step(9)
        job_name = 'cvp-tempest'
        job_parameters = {
             'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        }
        run_cvp_tempest = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert run_cvp_tempest == 'SUCCESS'
