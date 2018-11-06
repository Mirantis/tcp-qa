#    Copyright 2018 Mirantis, Inc.
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


class TestMcpInstallQueensCeph(object):
    """Test class for testing mcp queens ceph deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cookied_mcp_queens_dvr_ceph
    def test_cookied_mcp_queens_dvr_ceph(self, underlay,
                                         openstack_deployed,
                                         tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()

        LOG.info("*************** DONE **************")


class TestMcpInstallQueensOvs(object):
    """Test class for testing mcp queens ovs deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cookied_mcp_queens_ovs
    def test_cookied_mcp_queens_ovs(self, underlay,
                                    openstack_deployed,
                                    stacklight_deployed,
                                    tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.cookied_mcp_queens_ovs
    def test_cookied_mcp_queens_ovs_sl(self, underlay,
                                       openstack_deployed,
                                       stacklight_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run stacklight tests

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        stacklight_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")


class TestMcpInstallQueensDvr(object):
    """Test class for testing mcp queens dvr deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.test_cookied_mcp_queens_dvr
    def test_cookied_mcp_queens_dvr(self, underlay,
                                    openstack_deployed,
                                    stacklight_deployed,
                                    tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.test_cookied_mcp_queens_dvr
    def test_cookied_mcp_queens_dvr_sl(self, underlay,
                                       openstack_deployed,
                                       stacklight_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run stacklight tests

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        stacklight_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")


class TestMcpInstallQueensDvrSsl(object):
    """Test class for testing mcp queens dvr deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cookied_mcp_queens_dvr_ssl
    def test_cookied_mcp_queens_dvr_ssl(self, underlay,
                                        openstack_deployed,
                                        stacklight_deployed,
                                        tempest_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        if settings.RUN_TEMPEST:
            tempest_actions.prepare_and_run_tempest()

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cookied_mcp_queens_dvr_ssl
    def test_cookied_mcp_queens_dvr_ssl_sl(self, underlay,
                                           openstack_deployed,
                                           stacklight_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run stacklight tests

        """
        openstack_deployed._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        stacklight_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")
