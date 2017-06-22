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

LOG = logger.logger


@pytest.mark.deploy
class Testk8sInstall(object):
    """Test class for testing Kubernetes deploy"""

    @pytest.mark.fail_snapshot
    def test_k8s_install(self, sl_deployed, k8s_deployed, k8s_actions):
        """Test for deploying MCP environment with k8s+stacklight and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup stack light nodes
            5. Setup Kubernetes cluster
            6. Run conformance if need

        """
        k8s_actions.run_conformance()
        LOG.info("*************** DONE **************")

    @pytest.mark.fail_snapshot
    def test_only_k8s_install(self, k8s_deployed, k8s_actions):
        """Test for deploying MCP environment with k8s and check it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Run conformance if need

        """
        k8s_actions.run_conformance()
        LOG.info("*************** DONE **************")