#    Copyright 2019 Mirantis, Inc.
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


class TestUpdateContrail(object):
    @pytest.mark.day1_underlay
    def test_upgrade_pike_queens(self,
                                 show_step,
                                 underlay_actions,
                                 drivetrain_actions,
                                 reclass_actions,
                                 salt_actions):
        """Execute Contrail upgrade

        Scenario:
            1. Perform Contrail upgarde
            2. If jobs are passed then start tests with cvp-sanity job
            3. Run tests with cvp-tempest job
        """
        cfg_node = underlay_actions.get_target_node_names(target='cfg')[0]
        LOG.info('cfg node is {}'.format(cfg_node))
        verbose = True
        dt = drivetrain_actions
        # ########## Upgrade Contrail ###########
        show_step(1)
        LOG.info('Upgrade control VMs')
        job_name = 'deploy-update-opencontrail4'
        update_control_vms = dt.start_job_on_cid_jenkins(
            job_name=job_name)
        assert update_control_vms == 'SUCCESS'
        # ######################## Run CPV ##########################
        show_step(2)
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
        show_step(3)
        job_name = 'cvp-tempest'
        job_parameters = {
             'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        }
        run_cvp_tempest = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)
        assert run_cvp_tempest == 'SUCCESS'
