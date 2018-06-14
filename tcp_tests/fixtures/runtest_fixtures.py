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
from tcp_tests import settings
from tcp_tests.managers.runtestmanager import RuntestManager


@pytest.fixture(scope='function')
def tempest_actions(underlay, salt_actions):
    """
    Run tempest tests
    """
    tempest_threads = settings.TEMPEST_THREADS
    tempest_exclude_test_args = settings.TEMPEST_EXCLUDE_TEST_ARGS
    tempest_pattern = settings.TEMPEST_PATTERN
    cluster_name = settings.LAB_CONFIG_NAME
    domain_name = settings.DOMAIN_NAME
    target = settings.TEMPEST_TARGET
    runtest = RuntestManager(
        underlay, salt_actions,
        cluster_name=cluster_name,
        domain_name=domain_name,
        tempest_threads=tempest_threads,
        tempest_exclude_test_args=tempest_exclude_test_args,
        tempest_pattern=tempest_pattern,
        target=target)
    return runtest
