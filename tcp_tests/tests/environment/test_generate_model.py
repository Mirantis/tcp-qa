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

from tcp_tests import logger
from tcp_tests.helpers import ext

LOG = logger.logger


class TestGenerateModel(object):
    """Test class that generates and checks a cluster model"""

    @pytest.mark.fail_snapshot
    def test_generate_model(self, config, underlay, salt_actions):
        config.salt.salt_master_host = \
            underlay.host_by_node_role(
                node_role=ext.UNDERLAY_NODE_ROLES.salt_master)

        commands = underlay.read_template(config.salt_deploy.salt_steps_path)
        salt_actions.install(commands)

        LOG.info("*************** DONE **************")
