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


class TestMaasStandalone(object):
    """Test class for testing TCP deployment"""

    @pytest.mark.fail_snapshot
    def test_install_maas_standalone(self, config, underlay):
        """Install a VM with standalone maas

        Before using, please set the correct roles and timeout:

            export ROLES='["maas_master"]'
            export BOOTSTRAP_TIMEOUT=900

        , and unset these variables after the bootstrap is completed.

        Scenario:
            1. Install MaaS service and helper services
            2. Download Ubuntu cloud image and calculate MD5
            3. export environment variables to further use

        """

        nodes = underlay.node_names()
        host = underlay.host_by_node_name(nodes[0])
        maas_url = 'http://{0}:5240/'.format(host)
        LOG.info("MaaS url: {}".format(maas_url))
