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
import time
import socket
import urlparse

from tcp_tests import logger
from tcp_tests.managers.jenkins.client import JenkinsClient
# from tcp_tests import settings

from tcp_tests import managers

LOG = logger.logger

class TestUpdatePikeToQueens(object):
    """
    Created by https://mirantis.jira.com/browse/PROD-32683
    """

    @pytest.mark.grab_versions
    # @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_upgrade_pike_queens
    def test_upgrade_pike_queens(self, drivetrain_actions,
                                 show_step, _):
        """Execute upgrade from Pike to Queens

        Scenario:
            1. Perform the pre-upgrade activities
            2. Upgrade the OpenStack extra components
            3. Upgrade the OpenStack control plane
            4. Upgrade the OpenStack data plane
            5. Perform the post-upgrade activities
            6. If jobs are passed then start tests with cvp-sanity job
            7. Run tests with cvp-tempest job
        """
        # dt = drivetrain_actions
        cfg_node = 'cfg01.virtual-mcp-pike-dvr.local'
        # ############ Perform the pre-upgrade activities ###########
        show_step(1)
        for i in ['nova', 'cinder-manage']:
            underlay.check_call(
                node_name=cfg_node, verbose=verbose,
                cmd="salt ctl01* {} db online_data_migrations".format(i))
        # ########## Upgrade the OpenStack extra components #########
        show_step(2)
        # ########## Upgrade the OpenStack control plane  ###########
        show_step(3)
        # ############ Upgrade the OpenStack data plane  ############
        show_step(4)
        # ############ Perform the post-upgrade activities ##########
        show_step(5)
        # ######################## Run CPV ##########################
        show_step(6)
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

        assert run_cvp_sanity == 'SUCCESS'
        # ######################## Run Tempest #######################
        show_step(7)
        # job_name = 'cvp-tempest'
        # job_parameters = {
        #      'TEMPEST_ENDPOINT_TYPE': 'internalURL'
        # }
        # run_cvp_tempest = dt.start_job_on_cid_jenkins(
        #     job_name=job_name,
        #     job_parameters=job_parameters)

        # assert run_cvp_tempest == 'SUCCESS'
