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

import time

from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


@pytest.mark.deploy
class Test_Mcp11_install(object):
    """Test class for testing mcp11 vxlan deploy"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cz8119
    def test_mcp11_ocata_ovs_install(self, underlay,
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
    @pytest.mark.cz8119
    def test_mcp11_ocata_ovs_sl_install(self, underlay, config,
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
    @pytest.mark.cz8119
    @pytest.mark.revert_snapshot("sl_deployed")
    def test_mcp11_ocata_ovs_sl_kill_prometheus_service(self, underlay, config,
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
        8. Kill prometheus server service
        10. Check current prometheus targets are UP
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        11. Run SL component tests
        12. Download SL component tests report
        """

        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]
        LOG.info("Prometheus server nodes - {}".format(p_nodes))

        sl_deployed._salt.local(
            tgt=p_nodes[0],
            fun='cmd.run',
            args=["kill -9 $(pidof /opt/prometheus/prometheus)"]
        )

        sl_deployed.check_prometheus_targets(mon_nodes)

        LOG.info("Wait 10 sec for recover Prometheus server".format(p_nodes))
        time.sleep(10)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        assert len(p_nodes) == 2, "Prometheus server didn't recover while 10 sec"  # noqa

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
    @pytest.mark.cz8119
    @pytest.mark.revert_snapshot("sl_deployed")
    def test_mcp11_ocata_ovs_sl_kill_prometheus_container(self, underlay,
                                                          config,
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
        8. Kill prometheus server container
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        11. Run SL component tests
        12. Download SL component tests report
        """
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'  # noqa
                }
            })['return'][0]
        p_nodes_names = [n for n in p_nodes if len(p_nodes[n]) > 0]
        LOG.info("Prometheus server nodes - {}".format(p_nodes_names))

        container_id = p_nodes[p_nodes_names[0]].keys()[0]

        r = sl_deployed._salt.local(
            tgt=p_nodes_names[0],
            fun='dockerng.kill',
            args=["{}".format(container_id)]
        )['return'][0]

        assert r[p_nodes_names[0]]['result'], "Killing prometheus container failed" # noqa

        sl_deployed.check_prometheus_targets(mon_nodes)

        LOG.info("Wait 10 sec for recover Prometheus server".format(p_nodes))
        time.sleep(10)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        assert len(p_nodes) == 2, "Prometheus server didn't recover while 10 sec"  # noqa

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
    @pytest.mark.cz8119
    @pytest.mark.revert_snapshot("sl_deployed")
    def test_mcp11_ocata_ovs_sl_poweroff_prometheus_node(self, underlay,
                                                         config,
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
        8. Power off node with prometheus server
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        8. Power on node with prometheus server
        9. Check that docker services are running
        10. Check current prometheus targets are UP
        11. Run SL component tests
        12. Download SL component tests report
        """
        mon_nodes = sl_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))

        sl_deployed.check_prometheus_targets(mon_nodes)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'  # noqa
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        underlay.sudo_check_call(cmd="poweroff -f", node_name=p_nodes[0])

        sl_deployed.check_prometheus_targets(mon_nodes)

        LOG.info("Wait 60 sec for recover Prometheus server".format(p_nodes))
        time.sleep(60)

        p_nodes = sl_deployed._salt.local(
            tgt="I@prometheus:server",
            fun="dockerng.ps",
            kwargs={
                'filters': {
                    'label': 'com.docker.swarm.service.name=monitoring_server'
                }
            })['return'][0]
        p_nodes = [n for n in p_nodes if len(p_nodes[n]) > 0]

        assert len(p_nodes) == 2, "Prometheus server didn't recover while 60 sec"  # noqa

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
    @pytest.mark.cz8120
    def test_mcp11_ocata_dvr_install(self,
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
    @pytest.mark.cz8120
    def test_mcp11_ocata_dvr_sl_install(self, underlay, config,
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

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8117
    def test_mcp11_ocata_dpdk_install(self, underlay, openstack_deployed,
                                      show_step):
        """Test for deploying an mcp dpdk environment and check it
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    @pytest.mark.cz8117
    def test_mcp11_ocata_dvr_decapod_install(self, underlay, decapod_deployed,
                                             openstack_deployed, show_step):
        """Test for deploying an mcp dpdk environment and check it

        :type list: decapod_deployed.decapod_nodes , list of
                    config.underlay.ssh objects filtered for decapod roles.
        Scenario:
        1. Prepare salt on hosts
        2. Setup controller nodes
        3. Setup compute nodes
        """
        LOG.info("*************** DONE **************")
