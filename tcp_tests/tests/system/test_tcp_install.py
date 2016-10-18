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

import pytest

import base_test
from tcp_tests import settings
from tcp_tests.helpers import ext


@pytest.mark.deploy
class TestTCPInstaller(object):
    """Test class for testing TCP deployment"""

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_tcp_install_default(self, underlay, tcp_actions, show_step):
        """Test for deploying an tcp environment and check it

        Preconditions:
            1. Environment with installed salt master and salt minions
            2. Installed TCP salt formulas on salt master

        Scenario:
            1. Show TCP config
        """

        show_step(1)
        tcp_actions.show_tcp_config()
