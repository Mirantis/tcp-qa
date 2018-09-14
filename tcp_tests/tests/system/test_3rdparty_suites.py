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

from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class Test3rdpartySuites(object):
    """Test class for running 3rdparty test suites

    Requires environment variables:
      ENV_NAME
      LAB_CONFIG_NAME
      TESTS_CONFIGS
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_tempest
    def test_run_tempest(self, tempest_actions, show_step, _):
        """Runner for Juniper contrail-tests

        Scenario:
            1. Run tempest
        """
        show_step(1)
        tempest_actions.prepare_and_run_tempest()

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_stacklight
    def test_run_stacklight(self, sl_actions, show_step, _):
        """Runner for Stacklight tests

        Scenario:
            1. Run SL test
        """

        # Run SL component tetsts
        show_step(1)
        sl_actions.setup_sl_functional_tests(
                'cfg01',
        )
        sl_actions.run_sl_functional_tests(
                'cfg01',
                '/root/stacklight-pytest/stacklight_tests/',
                'tests/prometheus',
                'test_alerts.py',
                junit_report_name='stacklight_report.xml')
        # Download report
        sl_actions.download_sl_test_report(
                'cfg01',
                '/root/stacklight-pytest/stacklight_tests/'
                'stacklight_report.xml')

    @pytest.mark.grab_versions
    @pytest.mark.extract(container_system='docker', extract_from='conformance',
                         files_to_extract=['report'])
    @pytest.mark.merge_xunit(path='/root/report',
                             output='/root/conformance_result.xml')
    @pytest.mark.grab_k8s_results(name=['k8s_conformance.log',
                                        'conformance_result.xml'])
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.k8s_conformance
    def test_run_k8s_conformance(self, show_step, config, k8s_actions,
                                 k8s_logs, _):
        """Test run of k8s conformance tests"""
        k8s_actions.run_conformance()

    @pytest.mark.grab_versions
    @pytest.mark.grab_k8s_results(name=['virtlet_conformance.log',
                                        'report.xml'])
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.k8s_conformance_virtlet
    def test_run_k8s_conformance_virtlet(self, show_step, config, k8s_actions,
                                         k8s_logs, _):
        """Test run of k8s virtlet conformance tests"""
        k8s_actions.run_virtlet_conformance()
