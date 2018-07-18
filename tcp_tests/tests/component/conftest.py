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

from tcp_tests.fixtures.common_fixtures import *  # noqa
from tcp_tests.fixtures.ceph_fixtures import *  # noqa
from tcp_tests.fixtures.config_fixtures import *  # noqa
from tcp_tests.fixtures.underlay_fixtures import *  # noqa
from tcp_tests.fixtures.rally_fixtures import *  # noqa
from tcp_tests.fixtures.salt_fixtures import *  # noqa
from tcp_tests.fixtures.core_fixtures import *  # noqa
from tcp_tests.fixtures.openstack_fixtures import *  # noqa
from tcp_tests.fixtures.opencontrail_fixtures import *  # noqa
from tcp_tests.fixtures.oss_fixtures import *  # noqa
from tcp_tests.fixtures.decapod_fixtures import *  # noqa
from tcp_tests.fixtures.stacklight_fixtures import *  # noqa
from tcp_tests.fixtures.k8s_fixtures import *  # noqa
from tcp_tests.fixtures.drivetrain_fixtures import *  # noqa
from tcp_tests.fixtures.runtest_fixtures import * # noqa


__all__ = sorted([  # sort for documentation
    # common_fixtures
    'show_step',
    'func_name',
    # config_fixtures
    'config',
    # rally_fixtures
    'rally',
    # salt_fixtures
    'salt_actions',
    # core_fixtures
    'core_actions',
    # openstack_fixtures
    'openstack_actions',
    # oss_fixtures
    'oss_actions',
    # drivetrain_fixtures
    'drivetrain_actions',
    # decapod_fixtures
    'decapod_actions',
    # component fixtures
    'opencontrail',
    # stacklight_fixtures
    'sl_actions',
    'ceph_action',
    # k8s fixtures
    'k8s_actions',
    # tempest
    'tempest_actions'
])
