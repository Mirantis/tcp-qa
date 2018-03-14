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


@pytest.mark.deploy
class TestMcpInstallOvsPike(object):
    """Test class for testing mcp11 vxlan deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs
    def test_mcp_pike_ovs_install(self, underlay,
                                  openstack_deployed,
                                  openstack_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_actions._salt.local(
                tgt='*', fun='cmd.run',
                args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_sl
    def test_mcp_pike_ovs_sl_install(self, underlay, config,
                                     openstack_deployed,
                                     sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Download SL component tests report
        """
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tetsts
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_dvr
    def test_mcp_pike_dvr_install(self,
                                  underlay,
                                  openstack_deployed,
                                  openstack_actions):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_ovs_dvr_sl
    def test_mcp_pike_dvr_sl_install(self, underlay, config,
                                     openstack_deployed,
                                     sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Get monitoring nodes
        5. Check that docker services are running
        6. Check current prometheus targets are UP
        7. Run SL component tests
        8. Download SL component tests report
        """

        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        # Run SL component tests
        sl_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests/prometheus',
            'test_alerts.py')

        # Download report
        sl_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_mcp_pike_dpdk_install(self, underlay, openstack_deployed,
                                   show_step, openstack_actions):
        """Test for deploying an mcp dpdk environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_cookied_ovs_sl
    def test_mcp_pike_cookied_ovs_install(self, underlay,
                                          openstack_deployed,
                                          openstack_actions,
                                          sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        4. Run tempest

        """
        openstack_actions._salt.local(
                tgt='*', fun='cmd.run',
                args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.pike_cookied_ovs_dvr_sl
    def test_mcp_pike_cookied_dvr_install(self,
                                          underlay,
                                          openstack_deployed,
                                          openstack_actions,
                                          sl_deployed):
        """Test for deploying an mcp environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes

        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")


    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_mcp_pike_cookied_dpdk_install(self, underlay, openstack_deployed,
                                           show_step, openstack_actions):
        """Test for deploying an mcp dpdk environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        if settings.RUN_TEMPEST:
            openstack_actions.run_tempest(pattern=settings.PATTERN)
            openstack_actions.download_tempest_report()
        LOG.info("*************** DONE **************")

