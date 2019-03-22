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
import os

import pytest

from tcp_tests import logger
from tcp_tests import settings_oslo
from tcp_tests.helpers import utils

LOG = logger.logger


@pytest.fixture(scope='session')
def config():
    """Get the global config options from oslo.config INI file"""
    config_files = []

    tests_configs = os.environ.get('TESTS_CONFIGS', None)
    if tests_configs:
        for test_config in tests_configs.split(','):
            config_files.append(test_config)

    LOG.info("\n" + "-" * 10 + " Initialize oslo.config variables with "
             "defaults from environment" + "-" * 10)
    config_opts = settings_oslo.load_config(config_files)

    if os.path.isfile(config_opts.underlay.ssh_key_file):
        LOG.debug('Loading SSH key from file: {0}'.format(
            config_opts.underlay.ssh_key_file))
        key_from_file = utils.load_keyfile(config_opts.underlay.ssh_key_file)
        if key_from_file not in config_opts.underlay.ssh_keys:
            config_opts.underlay.ssh_keys.append(key_from_file)
    else:
        if not config_opts.underlay.ssh_keys:
            config_opts.underlay.ssh_keys.append(utils.generate_keys())
        utils.dump_keyfile(config_opts.underlay.ssh_key_file,
                           config_opts.underlay.ssh_keys[0])
        LOG.debug('Saving SSH key to file: {0}'.format(
            config_opts.underlay.ssh_key_file))
        utils.dump_keyfile(config_opts.underlay.ssh_key_file,
                           config_opts.underlay.ssh_keys[0])

    return config_opts
