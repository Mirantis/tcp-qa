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
from retry import retry

from tcp_tests.helpers import exceptions
from tcp_tests import logger
from tcp_tests.utils import get_jenkins_nodes

LOG = logger.logger


@pytest.mark.check_cicd
def test_check_cicd(config, underlay_actions, salt_actions, show_step):
    """Check CICD components
    Scenario:
        1. Get CICD Jenkins access credentials from salt
        2. Wait until all Jenkins nodes from pillar data are online
    """
    @retry(exceptions.DriveTrainError, delay=20, tries=20)
    def wait_for_slave_nodes(expected_nodes, jenkins_url,
                             jenkins_user, jenkins_pass):

        nodes = get_jenkins_nodes.get_nodes(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass)
        LOG.info("Jenkins nodes status: {}".format(nodes))

        node_names = [node['name'] for node in nodes]
        if set(expected_nodes) != set(node_names):
            raise exceptions.DriveTrainError(
                "Jenkins slave nodes are not added: expected {0}, actual {1}"
                .format(expected_nodes, node_names))

        if any(node['offline'] for node in nodes):
            raise exceptions.DriveTrainError(
                "Some jenkins slave nodes are offline: {0}"
                .format(nodes))

    salt = salt_actions
    show_step(1)

    tgt = 'I@docker:client:stack:jenkins and cid01*'
    jenkins_host = salt.get_single_pillar(
        tgt=tgt, pillar="jenkins:client:master:host")
    jenkins_port = salt.get_single_pillar(
        tgt=tgt, pillar="jenkins:client:master:port")
    jenkins_url = 'http://{0}:{1}'.format(jenkins_host, jenkins_port)
    jenkins_user = salt.get_single_pillar(
        tgt=tgt, pillar="jenkins:client:master:username")
    jenkins_pass = salt.get_single_pillar(
        tgt=tgt, pillar="jenkins:client:master:password")
    pillar_nodes = salt.get_single_pillar(
        tgt=tgt, pillar="jenkins:client:node")

    show_step(2)
    expected_nodes = pillar_nodes.keys()
    LOG.debug("Expected Jenkins nodes list: {}".format(expected_nodes))
    wait_for_slave_nodes(expected_nodes,
                         jenkins_url,
                         jenkins_user,
                         jenkins_pass)

    LOG.info("*************** DONE **************")
