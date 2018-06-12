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

from tcp_tests.helpers import ext
from tcp_tests.helpers import utils
from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.managers import envmanager_devops
from tcp_tests.managers import envmanager_empty
from tcp_tests.managers import underlay_ssh_manager

LOG = logger.logger


@pytest.fixture(scope="session")
def hardware(request, config):
    """Fixture for manage the hardware layer.

       - start/stop/reboot libvirt/IPMI(/MaaS?) nodes
       - snapshot/revert libvirt nodes (fuel-devops only)
       - block/unblock libvirt  networks/interfaces (fuel-devops only)

       This fixture should get a hardware configuration from
       'config' object or create a virtual/baremetal underlay
       using EnvironmentManager.

       Creates a snapshot 'hardware' with ready-to-use virtual environment
       (Only for config.hardware.manager='devops'):
        - just created virtual nodes in power-on state
        - node volumes filled with necessary content
        - node network interfaces connected to necessary devices

       config.hardware.manager: one of ('devops', 'maas', None)
       config.hardware.config: path to the config file for the manager
       config.hardware.current_snapshot = Latest created or reverted snapshot

       :rtype EnvironmentModel: if config.hardware.manager == 'devops'
       :rtype EnvironmentManagerEmpty: if config.hardware.manager == 'empty'
    """
    env = None

    manager = config.hardware.manager

    if manager == 'empty':
        # No environment manager is used.
        # 'config' should contain config.underlay.ssh settings
        # 'config' should contain config.underlay.current_snapshot setting
        env = envmanager_empty.EnvironmentManagerEmpty(config=config)

    elif manager == 'devops':
        # fuel-devops environment manager is used.
        # config.underlay.ssh settings can be empty or witn SSH to existing env
        # config.underlay.current_snapshot
        env = envmanager_devops.EnvironmentManager(config=config)
    else:
        raise Exception("Unknown hardware manager: '{}'".format(manager))

    # for devops manager: power on nodes and wait for SSH
    # for empty manager: do nothing
    # for maas manager: provision nodes and wait for SSH
    if not env.has_snapshot(ext.SNAPSHOT.hardware):
        env.create_snapshot(ext.SNAPSHOT.hardware)

    def fin():
        if settings.SHUTDOWN_ENV_ON_TEARDOWN:
            LOG.info("Shutdown environment...")
            env.stop()

    request.addfinalizer(fin)
    return env


@pytest.fixture(scope='function')
def revert_snapshot(request, hardware):
    """Revert snapshot for the test case

    Usage:
    @pytest.mark.revert_snapshot(name='<required_snapshot_name>')

    If the mark 'revert_snapshot' is absend, or <required_snapshot_name>
    not found, then an initial 'hardware' snapshot will be reverted.

    :rtype string: name of the reverted snapshot or None
    """
    top_fixtures_snapshots = utils.get_top_fixtures_marks(
        request, 'revert_snapshot')

    # Try to revert the best matches snapshot for the test
    for snapshot_name in top_fixtures_snapshots:
        if hardware.has_snapshot(snapshot_name) and \
                hardware.has_snapshot_config(snapshot_name):
            hardware.revert_snapshot(snapshot_name)
            return snapshot_name

    # Fallback to the basic snapshot
    hardware.revert_snapshot(ext.SNAPSHOT.hardware)
    return None


@pytest.fixture(scope='function')
def snapshot(request, hardware):
    """Fixture for creating snapshot at the end of test if it's needed

    Marks:
        snapshot_needed(name=None) - make snapshot if test is passed. If
        name argument provided, it will be used for creating snapshot,
        otherwise, test function name will be used

        fail_snapshot - make snapshot if test failed

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    snapshot_needed = request.keywords.get('snapshot_needed', None)
    fail_snapshot = request.keywords.get('fail_snapshot', None)

    def test_fin():
        default_snapshot_name = getattr(request.node.function,
                                        '_snapshot_name',
                                        request.node.function.__name__)
        if hasattr(request.node, 'rep_call') and request.node.rep_call.passed \
                and snapshot_needed:
            snapshot_name = utils.extract_name_from_mark(snapshot_needed) or \
                "{}_passed".format(default_snapshot_name)
            hardware.create_snapshot(snapshot_name, force=True)

        elif hasattr(request.node, 'rep_setup') and \
                request.node.rep_setup.failed and fail_snapshot:
            snapshot_name = "{0}_prep_failed".format(default_snapshot_name)
            hardware.create_snapshot(snapshot_name, force=True)

        elif hasattr(request.node, 'rep_call') and \
                request.node.rep_call.failed and fail_snapshot:
            snapshot_name = "{0}_failed".format(default_snapshot_name)
            hardware.create_snapshot(snapshot_name, force=True)

    request.addfinalizer(test_fin)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
@pytest.fixture(scope="function")
def underlay(request, revert_snapshot, config, hardware):
    """Fixture that should provide SSH access to underlay objects.

    - Starts the 'hardware' environment and creates 'underlay' with required
      configuration.
    - Fills the following object using the 'hardware' fixture:
      config.underlay.ssh = JSONList of SSH access credentials for nodes.
                            This list will be used for initialization the
                            model UnderlaySSHManager, see it for details.

    :rtype UnderlaySSHManager: Object that encapsulate SSH credentials;
                               - provide list of underlay nodes;
                               - provide SSH access to underlay nodes using
                                 node names or node IPs.
    """
    # Create Underlay

    def basic_underlay():
        # If config.underlay.ssh wasn't provided from external config, then
        # try to get necessary data from hardware manager (fuel-devops)

        # for devops manager: power on nodes and wait for SSH
        # for empty manager: do nothing
        # for maas manager: provision nodes and wait for SSH
        hardware.start(underlay_node_roles=config.underlay.roles,
                       timeout=config.underlay.bootstrap_timeout)

        config.underlay.ssh = hardware.get_ssh_data(
            roles=config.underlay.roles)

        LOG.info("Config - {}".format(config))
        underlay = underlay_ssh_manager.UnderlaySSHManager(config)

        if not config.underlay.lvm:
            underlay.enable_lvm(hardware.lvm_storages())
            config.underlay.lvm = underlay.config_lvm

        hardware.create_snapshot(ext.SNAPSHOT.underlay)

        return underlay

    def day1_underlay():
        hardware.start(
            underlay_node_roles=['salt_master'],
            timeout=config.underlay.bootstrap_timeout)

        config.underlay.ssh = hardware.get_ssh_data(
            roles=config.underlay.roles)

        underlay = underlay_ssh_manager.UnderlaySSHManager(config)

        LOG.info("Generate MACs for MaaS")
        macs = {
            n.name.split('.')[0]: {
                "interface": {
                    "mac": n.get_interface_by_network_name('admin').mac_address},  # noqa
                "power_parameters": {
                    "power_address": "{}:{}".format(
                        n.get_interface_by_network_name('admin').l2_network_device.address_pool.get_ip('l2_network_device'),  # noqa
                        n.bmc_port
                        )}} for n in hardware.slave_nodes}

        config.day1_cfg_config.maas_machines_macs = {
            "parameters": {
                "maas": {
                    "region": {
                        "machines": macs}}}}

        if not config.underlay.lvm:
            underlay.enable_lvm(hardware.lvm_storages())
            config.underlay.lvm = underlay.config_lvm

        for node in hardware.slave_nodes:
            # For correct comissioning by MaaS nodes should be powered off
            node.destroy()

        hardware.create_snapshot(ext.SNAPSHOT.underlay)

        return underlay

    if not config.underlay.ssh:
        if request.node.get_marker('day1_underlay'):
            underlay = day1_underlay()
        else:
            underlay = basic_underlay()

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        underlay = underlay_ssh_manager.UnderlaySSHManager(config)

    return underlay


@pytest.fixture(scope='function')
def grab_versions(request, func_name, underlay):
    """Fixture for grab package versions at the end of test

    Marks:
        grab_versions(name=None) - make snapshot if test is passed. If
        name argument provided, it will be used for creating data,
        otherwise, test function name will be used

    """
    grab_version = request.keywords.get('grab_versions', None)

    def test_fin():
        fixture_failed = (hasattr(request.node, 'rep_setup') and
                          request.node.rep_setup.failed)
        test_passed = (hasattr(request.node, 'rep_call') and
                       request.node.rep_call.passed)
        test_failed = (hasattr(request.node, 'rep_call') and
                       request.node.rep_call.failed)

        if fixture_failed or test_passed or test_failed:
            artifact_name = utils.extract_name_from_mark(grab_version) or \
                "{}".format(func_name)
            underlay.get_logs(artifact_name)

    if grab_version:
        request.addfinalizer(test_fin)
