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

from tcp_tests import logger
from tcp_tests import settings
import pytest
LOG = logger.logger


@pytest.mark.deploy
class TestUpgradeStacklight(object):

    """Test class for testing OpenContrail on a TCP lab"""
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_upgrade_stacklight(self, underlay, config,
                                hardware, sl_actions, stacklight_deployed):
        """Runner

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Prepare tests
            5. Run tests
        """
# Upgrade SL
        lab_name = settings.LAB_CONFIG_NAME
        steps_path = 'templates/{0}/sl-upgrade.yaml'.format(lab_name)
        commands = underlay.read_template(steps_path)
        sl_actions.install(commands, label='Upgrade SL services')
        hardware.create_snapshot(name='sl_v1_upgraded')

        mon_nodes = stacklight_deployed.get_monitoring_nodes()
        LOG.debug('Mon nodes list {0}'.format(mon_nodes))


# Run SL component tetsts
        stacklight_deployed.run_sl_functional_tests(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/',
            'tests',
            'tests/prometheus')

# Download report
        stacklight_deployed.download_sl_test_report(
            'cfg01',
            '/root/stacklight-pytest/stacklight_tests/report.xml')
        LOG.info("*************** DONE **************")
