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
import copy
import time

import pytest

from tcp_tests import settings
from tcp_tests.helpers import ext
from tcp_tests import logger

LOG = logger.logger


@pytest.mark.deploy
class TestTCPInstaller(object):
    """Test class for testing TCP deployment"""

    #salt_cmd = 'salt -l debug '  # For debug output
    #salt_call_cmd = 'salt-call -l debug '  # For debug output
    salt_cmd = 'salt --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    salt_call_cmd = 'salt-call --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    #salt_cmd = 'salt --state-output=terse --state-verbose=False '  # For reduced output
    #salt_call_cmd = 'salt-call --state-output=terse --state-verbose=False '  # For reduced output

    # @pytest.mark.snapshot_needed
    # @pytest.mark.fail_snapshot
    def test_tcp_install_default(self, underlay, openstack_deployed,
                                 show_step, rally):
        """Test for deploying an tcp environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """
        LOG.info("*************** DONE **************")

    def test_tcp_install_run_rally(self, underlay, openstack_deployed,
                                 show_step, rally):
        """Test for deploying an tcp environment and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """
        # prepare rally
        rally.prepare()
        rally.pull_image()
        rally.run()
        # run tempest
        rally.run_tempest()

        res = rally.get_results()

        fail_msg = 'Tempest verification fails {}'.format(res)
        assert res['failures'] == 0, fail_msg

    # @pytest.mark.snapshot_needed
    # @pytest.mark.fail_snapshot
    def test_tcp_install_with_scripts(self, config, underlay, salt_deployed,
                                      show_step, rally):
        """Test for deploying an tcp environment with scripts and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes

        """

        cmd = 'cd /srv/salt/reclass/scripts/; ./bootstrap_all.sh'
        underlay.check_call(cmd, host=config.salt.salt_master_host, verbose=True)

        # prepare rally
        rally.prepare()
        rally.pull_image()
        rally.run()
        # run tempest
        rally.run_tempest()

        res = rally.get_results()

        fail_msg = 'Tempest verification fails {}'.format(res)
        assert res['failures'] == 0, fail_msg
