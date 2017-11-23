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

LOG = logger.logger
from tcp_tests import settings

@pytest.mark.deploy
class TestUpgradeStacklight(object):
    """Test class for testing OpenContrail on a TCP lab"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_upgrade_stacklight(self, underlay, config, hardware, sl_deployed):
        """Runner

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Prepare tests
            5. Run tests
        """
    # Upgrade SL
    steps_path = 'templates/{0}/sl-upgrade.yaml'.format(settings.LAB_CONFIG_NAME)
    commands = underlay.read_template(steps_path)
    sl_actions.install(commands, label='Upgrade SL services')
    hardware.create_snapshot(name='sl_v1_upgraded')

    # Workaround for keepalived hang issue after env revert from snapshot
    # see https://mirantis.jira.com/browse/PROD-12038
    LOG.warning('Restarting keepalived service on controllers...')
    sl_actions._salt.local(tgt='ctl*', fun='cmd.run',
                           args='systemctl restart keepalived.service')
    LOG.warning('Restarting keepalived service on mon nodes...')
    sl_actions._salt.local(tgt='mon*', fun='cmd.run',
                           args='systemctl restart keepalived.service')

    mon_nodes = sl_deployed.get_monitoring_nodes()
    LOG.debug('Mon nodes list {0}'.format(mon_nodes))


        # Run SL component tetsts
#        sl_deployed.run_sl_functional_tests(
#            'cfg01',
#            '/root/stacklight-pytest/stacklight_tests/',
#            'tests',
#            'tests/prometheus')

        # Download report
#        sl_deployed.download_sl_test_report(
#            'cfg01',
#            '/root/stacklight-pytest/stacklight_tests/report.xml')
#        LOG.info("*************** DONE **************")
        LOG.info("*************** DONE **************")
