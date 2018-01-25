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

from tcp_tests.helpers import ext
from tcp_tests.helpers import utils
from tcp_tests import logger
from tcp_tests.managers import k8smanager

LOG = logger.logger


@pytest.fixture(scope='function')
def k8s_actions(config, underlay, salt_deployed):
    """Fixture that provides various actions for K8S

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :param salt_deployed: fixture provides salt manager
    :rtype: K8SManager

    For use in tests or fixtures to deploy a custom K8S
    """
    return k8smanager.K8SManager(config, underlay, salt_deployed)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
@pytest.fixture(scope='function')
def k8s_deployed(revert_snapshot, request, config, hardware, underlay,
                 common_services_deployed, salt_deployed, k8s_actions):
    """Fixture to get or install k8s on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param common_services_deployed: fixture provides CommonServicesManager
    :param k8s_actions: fixture provides K8SManager instance
    :rtype: K8SManager

    If config.k8s.k8s_installed is not set, this fixture assumes
    that the k8s services were not installed, and do the following:
    - install k8s services
    - make snapshot with name 'k8s_deployed'
    - return K8SManager instance

    If config.k8s.k8s_installed was set, this fixture assumes that
    the k8s services were already installed, and do the following:
    - return K8SManager instance

    If you want to revert 'k8s_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("k8s_deployed")
    """

    # Deploy Kubernetes cluster
    if not config.k8s.k8s_installed:
        steps_path = config.k8s_deploy.k8s_steps_path
        commands = underlay.read_template(steps_path)
        k8s_actions.install(commands)
        hardware.create_snapshot(ext.SNAPSHOT.k8s_deployed)
        salt_deployed.sync_time()

    # Workaround for keepalived hang issue after env revert from snapshot
    # see https://mirantis.jira.com/browse/PROD-12038
    LOG.warning('Restarting keepalived service on controllers...')
    k8s_actions._salt.local(tgt='ctl*', fun='cmd.run',
                            args='systemctl restart keepalived.service')

    return k8s_actions


@pytest.fixture(scope='function')
def grab_virtlet_results(request, func_name, underlay, k8s_deployed):
    """Finalizer to extract virtlet conformance logs"""

    grab_virtlet_result = request.keywords.get('grab_virtlet_results', None)

    def test_fin():
        if hasattr(request.node, 'rep_call') and \
                (request.node.rep_call.passed or request.node.rep_call.failed)\
                and grab_virtlet_result:
            artifact_name = utils.extract_name_from_mark(grab_virtlet_result) \
                            or "{}".format(func_name)
            k8s_deployed.download_virtlet_conformance_log(artifact_name)
    request.addfinalizer(test_fin)
