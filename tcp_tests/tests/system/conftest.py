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

#from tcp_tests.fixtures import *
from tcp_tests.fixtures.common_fixtures import *
from tcp_tests.fixtures.config_fixtures import *
from tcp_tests.fixtures.underlay_fixtures import *
from tcp_tests.fixtures.rally_fixtures import *
from tcp_tests.fixtures.salt_fixtures import *
from tcp_tests.fixtures.common_services_fixtures import *
from tcp_tests.fixtures.openstack_fixtures import *
from tcp_tests.fixtures.opencontrail_fixtures import *
from tcp_tests.fixtures.oss_fixtures import *
from tcp_tests.fixtures.decapod_fixtures import *
from tcp_tests.fixtures.stacklight_fixtures import *
from tcp_tests.fixtures.virtlet_fixtures import *
from tcp_tests.fixtures.virtlet_ceph_fixtures import *
from tcp_tests.fixtures.k8s_fixtures import *


__all__ = sorted([  # sort for documentation
    # common_fixtures
    'show_step',
    'revert_snapshot',
    'snapshot',
    # config_fixtures
    'config',
    #underlay_fixtures
    'hardware',
    'underlay',
    # rally_fixtures
    'rally',
    # salt_fixtures
    'salt_actions',
    'salt_deployed',
    # common_services_fixtures
    'common_services_actions',
    'common_services_deployed',
    # openstack_fixtures
    'openstack_actions',
    'openstack_deployed',
    # oss_fixtures
    'oss_actions',
    'oss_deployed',
    # decapod_fixtures
    'decapod_actions',
    'decapod_deployed',
    # component fixtures
    'opencontrail',
    # stacklight_fixtures
    'sl_actions',
    'sl_deployed',
    # k8s fixtures
    'k8s_actions',
    'k8s_deployed',
    'virtlet_actions',
    'virtlet_deployed',
    'virtlet_ceph_actions',
    'virtlet_ceph_deployed'
])
