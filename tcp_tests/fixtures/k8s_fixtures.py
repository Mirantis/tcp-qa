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
def k8s_logs(request, func_name, underlay, k8s_deployed):
    """Finalizer to extract conformance logs

    Usage:
    @pytest.mark.grab_k8s_result(name=['file1', 'file2'])
    ^^^^^
    This mark says tcp-qa to download files that counted in array as
    parameter 'name'. Files should be located at ctl01. Files will be
    downloaded to the host, where your test runs.

    @pytest.mark.extract(container_system='docker', extract_from='conformance',
                         files_to_extract=['report'])
    ^^^^^
    This mark says tcp-qa to copy files from container. Docker or k8s system
    supported.
    container_system param says function what strategy should be
    used.
    extract_from param says what container should be used to copy. Note
    that we are using grep to determine container ID, so if you have multiple
    container with same substring to copy you may encounter unexpected issues.
    files_to_extract param - this is array with paths of files/dirs to copy.

    @pytest.mark.merge_xunit(path='/root/report',
                             output='/root/conformance_result.xml')
    ^^^^^
    This mark will help you to merge xunit results in case if you have
    multiple reports because of multiple threads.
    path param says where xml results stored
    output param says where result will be saved
    """

    grab_k8s_result = request.keywords.get('grab_k8s_results', None)
    extract = request.keywords.get('extract', None)
    merge_xunit = request.keywords.get('merge_xunit', None)

    def test_fin():
        if hasattr(request.node, 'rep_call') and \
                (request.node.rep_call.passed or request.node.rep_call.failed)\
                and grab_k8s_result:
            files = utils.extract_name_from_mark(grab_k8s_result) \
                    or "{}".format(func_name)
            if extract:
                container_system = utils.extract_name_from_mark(
                    extract, 'container_system')
                extract_from = utils.extract_name_from_mark(
                    extract, 'extract_from')
                files_to_extract = utils.extract_name_from_mark(
                    extract, 'files_to_extract')
                for path in files_to_extract:
                    k8s_deployed.extract_file_to_node(
                        system=container_system, container=extract_from,
                        file_path=path)
            else:
                k8s_deployed.extract_file_to_node()
            if merge_xunit:
                path = utils.extract_name_from_mark(merge_xunit, 'path')
                output = utils.extract_name_from_mark(merge_xunit, 'output')
                k8s_deployed.combine_xunit(path, output)
            k8s_deployed.download_k8s_logs(files)

    request.addfinalizer(test_fin)


@pytest.fixture(scope='function')
def cncf_log_helper(request, func_name, underlay, k8s_deployed):
    """Finalizer to prepare cncf tar.gz and save results from archive"""

    cncf_publisher = request.keywords.get('cncf_publisher', None)

    def test_fin():
        if hasattr(request.node, 'rep_call') and \
                (request.node.rep_call.passed or request.node.rep_call.failed)\
                and cncf_publisher:
            files = utils.extract_name_from_mark(cncf_publisher) \
                    or "{}".format(func_name)
            k8s_deployed.extract_file_to_node(
                system='k8s', file_path='tmp/sonobuoy',
                pod_name='sonobuoy', pod_namespace='sonobuoy'
            )
            k8s_deployed.manage_cncf_archive()
            k8s_deployed.download_k8s_logs(files)

    request.addfinalizer(test_fin)
