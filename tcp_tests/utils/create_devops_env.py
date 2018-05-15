#!/usr/bin/env python

from tcp_tests.helpers import ext
from tcp_tests.helpers import utils
from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.managers import envmanager_devops
from tcp_tests.managers import envmanager_empty
from tcp_tests.managers import underlay_ssh_manager

from tcp_tests.fixtures import config_fixtures

import os
import sys


import tcp_tests


def main():

    config = config_fixtures.config()

    env = envmanager_devops.EnvironmentManager(config=config)
    if not env.has_snapshot(ext.SNAPSHOT.hardware):
        env.create_snapshot(ext.SNAPSHOT.hardware)

    return

    if not config.underlay.ssh:
        # If config.underlay.ssh wasn't provided from external config, then
        # try to get necessary data from hardware manager (fuel-devops)
        # for devops manager: power on nodes and wait for SSH
        # for empty manager: do nothing
        # for maas manager: provision nodes and wait for SSH
        env.start(underlay_node_roles=config.underlay.roles,
                  timeout=config.underlay.bootstrap_timeout)

        config.underlay.ssh = env.get_ssh_data(
            roles=config.underlay.roles)

        underlay = underlay_ssh_manager.UnderlaySSHManager(config)

        if not config.underlay.lvm:
            underlay.enable_lvm(env.lvm_storages())
            config.underlay.lvm = underlay.config_lvm

        env.create_snapshot(ext.SNAPSHOT.underlay)

    # Print initial inventory: nodes IP, networks and masks (or specific info?)


if __name__ == '__main__':
    sys.exit(main())
