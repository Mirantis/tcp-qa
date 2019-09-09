#    Copyright 2017 Mirantis, Inc.
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

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests.utils import get_jenkins_job_stages
from tcp_tests.utils import run_jenkins_job

LOG = logger.logger


class TestFailoverCeph(object):
    """Test class for testing MCP Ceph failover"""

    TEMPEST_JOB_NAME = 'cvp-tempest'
    TEMPEST_JOB_PARAMETERS = {
            'TEMPEST_ENDPOINT_TYPE': 'internalURL',
            'TEMPEST_TEST_PATTERN': 'set=smoke'
    }

    SANITY_JOB_NAME = 'cvp-sanity'
    SANITY_JOB_PARAMETERS = {
        'EXTRA_PARAMS': {
            'envs': [
                "tests_set=-k "
                "'not test_ceph_health and not test_prometheus_alert_count'"
            ]
        }
    }

    JENKINS_START_TIMEOUT = 60
    JENKINS_BUILD_TIMEOUT = 60 * 15

    def get_ceph_health(self, ssh, node_names):
        """Get Ceph health status on specified nodes

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param node_names: list, full hostnames of Ceph OSD nodes
        :return: dict, Ceph health status from each OSD node (output of
            'ceph -s' command executed on each node)
        """
        return {
            node_name: ssh.check_call(
                "ceph -s",
                node_name=node_name,
                raise_on_err=False)['stdout_str']
            for node_name in node_names
        }

    @pytest.mark.grab_versions
    @pytest.mark.restart_osd_node
    def test_restart_osd_node(
            self,
            salt_actions,
            drivetrain_actions,
            underlay_actions,
            show_step):
        """Verify that Ceph OSD node is not affected by system restart

        Scenario:
        1. Find Ceph OSD nodes
        2. Check Ceph cluster health before node restart (skipped until
            PROD-31374 is fixed)
        3. Restart 1 Ceph OSD node
        4. Check Ceph cluster health after node restart (skipped until
            PROD-31374 is fixed)
        5. Run Tempest smoke test suite
        6. Run test_ceph_status.py::test_ceph_osd and
            test_services.py::test_check_services[osd] sanity tests

        Duration: ~9 min
        """
        salt = salt_actions
        ssh = underlay_actions
        dt = drivetrain_actions

        # Find Ceph OSD nodes
        show_step(1)
        tgt = "I@ceph:osd"
        osd_hosts = salt.local(tgt, "test.ping")['return'][0].keys()
        # Select a node for the test
        osd_host = osd_hosts[0]

        # Check Ceph cluster health before node restart
        show_step(2)
        ceph_health = self.get_ceph_health(ssh, osd_hosts)
        # FIXME: uncomment the check once PROD-31374 is fixed
        # status = all(
        #     ["OK" in status for node, status in ceph_health.items()])
        # assert status, "Ceph health is not OK: {0}".format(ceph_health)

        # Restart a Ceph OSD node
        show_step(3)
        LOG.info("Sending reboot command to '{}' node.".format(osd_host))
        remote = ssh.remote(node_name=osd_host)
        remote.execute_async("/sbin/shutdown -r now")

        # Wait for restarted node to boot and become accessible
        helpers.wait_pass(remote.reconnect, timeout=60 * 3, interval=5)
        echo_request = "echo"
        echo_response = salt.local(
            osd_host, "test.echo", echo_request)['return'][0]
        assert echo_request == echo_response[osd_host], (
            "Minion on node '{}' node is not responding after node "
            "reboot.".format(osd_host)
        )
        LOG.info("'{}' node is back after reboot.".format(osd_host))

        # Check Ceph cluster health after node restart
        show_step(4)
        ceph_health = self.get_ceph_health(ssh, osd_hosts)  # noqa
        # FIXME: uncomment the check once PROD-31374 is fixed
        # status = all(
        #     ["OK" in status for node, status in ceph_health.items()])
        # assert status, "Ceph health is not OK: {0}".format(ceph_health)

        # Run Tempest smoke test suite
        show_step(5)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.TEMPEST_JOB_NAME,
            job_parameters=self.TEMPEST_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )

        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing Tempest smoke "
            "tests".format(
                self.TEMPEST_JOB_NAME, status)
        )

        # Run Sanity test
        show_step(6)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.SANITY_JOB_NAME,
            job_parameters=self.SANITY_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing selected sanity "
            "tests".format(
                self.SANITY_JOB_NAME, status)
        )

    @pytest.mark.grab_versions
    @pytest.mark.restart_cmn_node
    def test_restart_cmn_node(
            self,
            salt_actions,
            drivetrain_actions,
            underlay_actions,
            show_step):
        """Verify that Ceph CMN node is not affected by system restart

        Scenario:
        1. Find Ceph CMN nodes
        2. Check Ceph cluster health before node restart (skipped until
            PROD-31374 is fixed)
        3. Restart 1 Ceph CMN node
        4. Check Ceph cluster health after node restart (skipped until
            PROD-31374 is fixed)
        5. Run Tempest smoke test suite
        6. Run test_ceph_status.py::test_ceph_replicas and
            test_services.py::test_check_services[cmn] sanity tests

        Duration: ~9 min
        """
        salt = salt_actions
        ssh = underlay_actions
        dt = drivetrain_actions

        # Find Ceph CMN nodes
        show_step(1)
        tgt = "I@ceph:mon"
        cmn_hosts = salt.local(tgt, "test.ping")['return'][0].keys()
        # Select a node for the test
        cmn_host = cmn_hosts[0]

        # Check Ceph cluster health before node restart
        show_step(2)
        ceph_health = self.get_ceph_health(ssh, cmn_hosts)
        # FIXME: uncomment the check once PROD-31374 is fixed
        # status = all(
        #     ["OK" in status for node, status in ceph_health.items()])
        # assert status, "Ceph health is not OK: {0}".format(ceph_health)

        # Restart a Ceph CMN node
        show_step(3)
        LOG.info("Sending reboot command to '{}' node.".format(cmn_host))
        remote = ssh.remote(node_name=cmn_host)
        remote.execute_async("/sbin/shutdown -r now")

        # Wait for restarted node to boot and become accessible
        helpers.wait_pass(remote.reconnect, timeout=60 * 3, interval=5)
        echo_request = "echo"
        echo_response = salt.local(
            cmn_host, "test.echo", echo_request)['return'][0]
        assert echo_request == echo_response[cmn_host], (
            "Minion on node '{}' node is not responding after node "
            "reboot.".format(cmn_host)
        )
        LOG.info("'{}' node is back after reboot.".format(cmn_host))

        # Check Ceph cluster health after node restart
        show_step(4)
        ceph_health = self.get_ceph_health(ssh, cmn_hosts) # noqa
        # FIXME: uncomment the check once PROD-31374 is fixed
        # status = all(
        #     ["OK" in status for node, status in ceph_health.items()])
        # assert status, "Ceph health is not OK: {0}".format(ceph_health)

        # Run Tempest smoke test suite
        show_step(5)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.TEMPEST_JOB_NAME,
            job_parameters=self.TEMPEST_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )

        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing Tempest smoke "
            "tests".format(
                self.TEMPEST_JOB_NAME, status)
        )

        # Run Sanity test
        show_step(6)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.SANITY_JOB_NAME,
            job_parameters=self.SANITY_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing selected sanity "
            "tests".format(
                self.SANITY_JOB_NAME, status)
        )

    @pytest.mark.grab_versions
    @pytest.mark.restart_rgw_node
    def test_restart_rgw_node(
            self,
            salt_actions,
            drivetrain_actions,
            underlay_actions,
            show_step):
        """Verify that Ceph RGW node is not affected by system restart

        Scenario:
        1. Find Ceph RGW nodes
        2. Check Ceph cluster health before node restart (skipped until
            PROD-31374 is fixed)
        3. Restart 1 Ceph RGW node
        4. Check Ceph cluster health after node restart (skipped until
            PROD-31374 is fixed)
        5. Run Tempest smoke test suite
        6. Run test_services.py::test_check_services[rgw] sanity test

        Duration: ~9 min
        """
        salt = salt_actions
        ssh = underlay_actions
        dt = drivetrain_actions

        # Find Ceph RGW nodes
        show_step(1)
        tgt = "I@ceph:radosgw"
        rgw_hosts = salt.local(tgt, "test.ping")['return'][0].keys()
        # Select a node for the test
        rgw_host = rgw_hosts[0]

        # Check Ceph cluster health before node restart
        show_step(2)
        ceph_health = self.get_ceph_health(ssh, rgw_hosts)
        # FIXME: uncomment the check once PROD-31374 is fixed
        # status = all(
        #     ["OK" in status for node, status in ceph_health.items()])
        # assert status, "Ceph health is not OK: {0}".format(ceph_health)

        # Restart a Ceph RGW node
        show_step(3)
        LOG.info("Sending reboot command to '{}' node.".format(rgw_host))
        remote = ssh.remote(node_name=rgw_host)
        remote.execute_async("/sbin/shutdown -r now")

        # Wait for restarted node to boot and become accessible
        helpers.wait_pass(remote.reconnect, timeout=60 * 3, interval=5)
        echo_request = "echo"
        echo_response = salt.local(
            rgw_host, "test.echo", echo_request)['return'][0]
        assert echo_request == echo_response[rgw_host], (
            "Minion on node '{}' node is not responding after node "
            "reboot.".format(rgw_host)
        )
        LOG.info("'{}' node is back after reboot.".format(rgw_host))

        # Check Ceph cluster health after node restart
        show_step(4)
        ceph_health = self.get_ceph_health(ssh, rgw_hosts) # noqa
        # FIXME: uncomment the check once PROD-31374 is fixed
        # status = all(
        #     ["OK" in status for node, status in ceph_health.items()])
        # assert status, "Ceph health is not OK: {0}".format(ceph_health)

        # Run Tempest smoke test suite
        show_step(5)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.TEMPEST_JOB_NAME,
            job_parameters=self.TEMPEST_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )

        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing Tempest smoke "
            "tests".format(
                self.TEMPEST_JOB_NAME, status)
        )

        # Run Sanity test
        show_step(6)
        status = dt.start_job_on_cid_jenkins(
            job_name=self.SANITY_JOB_NAME,
            job_parameters=self.SANITY_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=self.JENKINS_BUILD_TIMEOUT
        )
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing selected sanity "
            "tests".format(
                self.SANITY_JOB_NAME, status)
        )

    # #######################################################################
    # ############# Tests for fuel-devops deployed environments #############
    # #######################################################################
    def show_failed_msg(self, failed):
        return "There are failed tempest tests:\n\n  {0}".format(
            '\n\n  '.join([(name + ': ' + detail)
                           for name, detail in failed.items()]))

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def _test_restart_osd_node(self, func_name, underlay, config,
                               openstack_deployed, ceph_deployed,
                               openstack_actions, hardware,
                               rally, show_step):
        """Test restart ceph osd node

        Scenario:
            1. Find ceph osd nodes
            2. Check ceph health before restart
            3. Restart 1 ceph osd node
            4. Check ceph health after restart
            5. Run tempest smoke after failover
            6. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
            - Ceph cluster
        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        # STEP #1
        show_step(1)
        osd_node_names = underlay.get_target_node_names(
            target='osd')

        # STEP #2
        show_step(2)
        # Get the ceph health output before restart
        health_before = self.get_ceph_health(underlay, osd_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_before))

        # STEP #3
        show_step(3)
        hardware.warm_restart_nodes(underlay, 'osd01')

        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        # STEP #4
        show_step(4)
        # Get the ceph health output after restart
        health_after = self.get_ceph_health(underlay, osd_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_after))

        rally.run_container()

        # STEP #5
        show_step(5)
        results = rally.run_tempest(pattern='set=smoke',
                                    conf_name='/var/lib/ceph_mcp.conf',
                                    report_prefix=func_name,
                                    designate_plugin=False,
                                    timeout=1800)
        # Step #6
        show_step(6)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def _test_restart_cmn_node(self, func_name, underlay, config,
                               openstack_deployed, ceph_deployed,
                               core_actions,
                               salt_actions, openstack_actions,
                               rally, show_step, hardware):
        """Test restart ceph cmn node

        Scenario:
            1. Find ceph cmn nodes
            2. Check ceph health before restart
            3. Restart 1 ceph cmn node
            4. Check ceph health after restart
            5. Run tempest smoke after failover
            6. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
            - Ceph cluster
        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')
        # STEP #1
        show_step(1)
        cmn_node_names = underlay.get_target_node_names(
            target='cmn')

        # STEP #2
        show_step(2)
        # Get the ceph health output before restart
        health_before = self.get_ceph_health(underlay, cmn_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_before))

        # STEP #3
        show_step(3)
        hardware.warm_restart_nodes(underlay, 'cmn01')

        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        # STEP #4
        show_step(4)
        # Get the ceph health output after restart
        health_after = self.get_ceph_health(underlay, cmn_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_after))

        rally.run_container()

        # STEP #5
        show_step(5)
        results = rally.run_tempest(pattern='set=smoke',
                                    conf_name='/var/lib/ceph_mcp.conf',
                                    report_prefix=func_name,
                                    designate_plugin=False,
                                    timeout=1800)
        # Step #6
        show_step(6)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def _test_restart_rgw_node(self, func_name, underlay, config,
                               openstack_deployed, ceph_deployed,
                               core_actions, hardware,
                               salt_actions, openstack_actions,
                               rally, show_step):
        """Test restart ceph rgw node

        Scenario:
            1. Find ceph rgw nodes
            2. Check ceph health before restart
            3. Restart 1 ceph rgw node
            4. Check ceph health after restart
            5. Run tempest smoke after failover
            6. Check tempest report for failed tests

        Requiremets:
            - Salt cluster
            - OpenStack cluster
            - Ceph cluster
        """
        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        # STEP #1
        show_step(1)
        rgw_node_names = underlay.get_target_node_names(
            target='rgw')
        if not rgw_node_names:
            pytest.skip('Skip as there are not rgw nodes in deploy')

        # STEP #2
        show_step(2)
        # Get the ceph health output before restart
        health_before = self.get_ceph_health(underlay, rgw_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_before))

        # STEP #3
        show_step(3)
        hardware.warm_restart_nodes(underlay, 'rgw01')

        openstack_actions._salt.local(
            tgt='*', fun='cmd.run',
            args='service ntp stop; ntpd -gq; service ntp start')

        # STEP #4
        show_step(4)
        # Get the ceph health output after restart
        health_after = self.get_ceph_health(underlay, rgw_node_names)
        assert all(["OK" in p for n, p in health_before.items()]), (
            "'Ceph health is not ok from node: {0}".format(health_after))

        rally.run_container()

        # STEP #5
        show_step(5)
        results = rally.run_tempest(pattern='set=smoke',
                                    conf_name='/var/lib/ceph_mcp.conf',
                                    designate_plugin=False,
                                    report_prefix=func_name,
                                    timeout=1800)
        # Step #6
        show_step(6)
        assert not results['fail'], self.show_failed_msg(results['fail'])

        LOG.info("*************** DONE **************")
