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

import collections


def enum(*values, **kwargs):
    names = kwargs.get('names')
    if names:
        return collections.namedtuple('Enum', names)(*values)
    return collections.namedtuple('Enum', values)(*values)


UNDERLAY_NODE_ROLES = enum(
    'salt_master',
    'salt_minion',
    'k8s_virtlet',
    'k8s_controller',
    'decapod_mon',
    'decapod_osd',
    'decapod_all',
)


NETWORK_TYPE = enum(
    'private',
    'admin'
)


SNAPSHOT = enum(
    'hardware',
    'underlay',
    'salt_deployed',
    'common_services_deployed',
    'oss_deployed',
    'drivetrain_deployed',
    'openstack_deployed',
    'sl_deployed',
    'virtlet_deployed',
    'virtlet_ceph_deployed',
    'k8s_deployed',
    'decapod_deployed',
    'ceph_deployed',
    'day1_underlay',
    'cfg_configured',
)


LOG_LEVELS = enum(
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL',
    'DEBUG',
    'NOTE'
)
