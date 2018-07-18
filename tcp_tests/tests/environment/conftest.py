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
from tcp_tests.fixtures.config_fixtures import *  # noqa
from tcp_tests.fixtures.underlay_fixtures import *  # noqa
from tcp_tests.fixtures.rally_fixtures import *  # noqa
from tcp_tests.fixtures.salt_fixtures import *  # noqa
from tcp_tests.fixtures.core_fixtures import *  # noqa
from tcp_tests.fixtures.openstack_fixtures import *  # noqa
from tcp_tests.fixtures.opencontrail_fixtures import *  # noqa

__all__ = sorted([  # sort for documentation
    # common_fixtures
    'show_step',
    'revert_snapshot',
    'snapshot',
    # config_fixtures
    'config',
    # underlay_fixtures
    'hardware',
    'underlay',
    # rally_fixtures
    'rally',
    # salt_fixtures
    'salt_actions',
    'salt_deployed',
    # core_fixtures
    'core_actions',
    'core_deployed',
    # openstack_fixtures
    'openstack_actions',
    'openstack_deployed',
    # component fixtures
    'opencontrail',
])
