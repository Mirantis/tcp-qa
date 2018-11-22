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
import time

from tcp_tests.helpers import ext
from tcp_tests.helpers import utils
from tcp_tests import logger
from tcp_tests.managers import k8smanager

LOG = logger.logger


@pytest.fixture(scope='function')
def k8s_actions(config, underlay_actions, salt_actions):
    """Fixture that provides various actions for K8S

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :param salt_deployed: fixture provides salt manager
    :rtype: K8SManager

    For use in tests or fixtures to deploy a custom K8S
    """
    return k8smanager.K8SManager(config, underlay_actions, salt_actions)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
@pytest.fixture(scope='function')
def k8s_deployed(revert_snapshot, request, config, hardware, underlay,
                 core_deployed, salt_deployed, k8s_actions):
    """Fixture to get or install k8s on environment

    :param revert_snapshot: fixture that reverts snapshot that is specified
                            in test with @pytest.mark.revert_snapshot(<name>)
    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param core_deployed: fixture provides CoreManager
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
        # Workaround for dhclient not killed on non-dhcp interfaces
        # see https://mirantis.jira.com/browse/PROD-22473
        tgt = 'I@kubernetes:pool'
        LOG.warning('Killing dhclient on every non-dhcp interface '
                    'on nodes with target={}'.format(tgt))
        interfaces_pillar = k8s_actions._salt.get_pillar(
            tgt=tgt, pillar='linux:network:interface')[0]

        for node_name, interfaces in interfaces_pillar.items():
            for iface_name, iface in interfaces.items():
                iface_name = iface.get('name', iface_name)
                default_proto = 'static' if 'address' in iface else 'dhcp'
                if iface.get('proto', default_proto) != 'dhcp':
                    LOG.warning('Trying to kill dhclient for iface {0} '
                                'on node {1}'.format(iface_name, node_name))
                    underlay.check_call(
                        cmd='pkill -f "dhclient.*{}"'.format(iface_name),
                        node_name=node_name, raise_on_err=False)

        LOG.warning('Restarting keepalived service on controllers...')
        k8s_actions._salt.local(tgt='ctl*', fun='cmd.run',
                                args='systemctl restart keepalived.service')
        # give some time to keepalived to enter in MASTER state
        time.sleep(3)
        # --- end of workaround

        # install k8s
        steps_path = config.k8s_deploy.k8s_steps_path
        commands = underlay.read_template(steps_path)
        k8s_actions.install(commands)

        hardware.create_snapshot(ext.SNAPSHOT.k8s_deployed)
        salt_deployed.sync_time()

    return k8s_actions


@pytest.fixture(scope='function')
def k8s_logs(request, func_name, k8s_actions):
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
                    k8s_actions.extract_file_to_node(
                        system=container_system, container=extract_from,
                        file_path=path)
            else:
                k8s_actions.extract_file_to_node()
            if merge_xunit:
                path = utils.extract_name_from_mark(merge_xunit, 'path')
                output = utils.extract_name_from_mark(merge_xunit, 'output')
                k8s_actions.combine_xunit(path, output)
            k8s_actions.download_k8s_logs(files)

    request.addfinalizer(test_fin)


@pytest.fixture(scope='function')
def k8s_cncf_log_helper(request, func_name, underlay, k8s_deployed):
    """Finalizer to prepare cncf tar.gz and save results from archive"""

    cncf_publisher = request.keywords.get('cncf_publisher', None)

    def test_fin():
        if hasattr(request.node, 'rep_call') and \
                (request.node.rep_call.passed or request.node.rep_call.failed)\
                and cncf_publisher:
            LOG.info("Waiting 60 sec for sonobuoy to generate results archive")
            time.sleep(60)
            LOG.info("Downloading sonobuoy results archive")
            files = utils.extract_name_from_mark(cncf_publisher) \
                    or "{}".format(func_name)
            k8s_deployed.extract_file_to_node(
                system='k8s', file_path='tmp/sonobuoy',
                pod_name='sonobuoy', pod_namespace='heptio-sonobuoy'
            )
            k8s_deployed.manage_cncf_archive()
            k8s_deployed.download_k8s_logs(files)

    request.addfinalizer(test_fin)


@pytest.fixture(scope='function')
def k8s_chain_update_log_helper(request, config, k8s_deployed):
    def test_fin():
        if hasattr(request.node, 'rep_call') and \
                (request.node.rep_call.passed or request.node.rep_call.failed):

            chain_versions = config.k8s.k8s_update_chain.split(" ")
            for version in chain_versions:
                container_name = "k8s-conformance:{}".format(version)
                tmp_report_dir = "/root/report_{}".format(version)
                report_path = "report_{}.xml".format(version)
                conformance_log_path = "k8s_conformance_{}.log".format(version)

                k8s_deployed.extract_file_to_node(
                    system='docker', container=container_name,
                    out_dir=tmp_report_dir, file_path='report'
                )
                k8s_deployed.combine_xunit(tmp_report_dir,
                                           '/root/{}'.format(report_path))

                k8s_deployed.download_k8s_logs(
                    [report_path, conformance_log_path])

    request.addfinalizer(test_fin)
