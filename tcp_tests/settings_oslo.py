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
import copy
import os
import pkg_resources

from oslo_config import cfg
from oslo_config import generator

from tcp_tests.helpers import ext
from tcp_tests.helpers import oslo_cfg_types as ct
from tcp_tests import settings


_default_conf = pkg_resources.resource_filename(
    __name__, 'templates/default.yaml')


hardware_opts = [
    ct.Cfg('manager', ct.String(),
           help="Hardware manager name", default="devops"),
    ct.Cfg('conf_path', ct.String(),
           help="Hardware config file", default=_default_conf),
    ct.Cfg('current_snapshot', ct.String(),
           help="Latest environment status name",
           default=ext.SNAPSHOT.hardware),
]


underlay_opts = [
    ct.Cfg('ssh', ct.JSONList(),
           help="""SSH Settings for Underlay: [{
                  'node_name': node1,
                  'host': hostname,
                  'login': login,
                  'password': password,
                  'address_pool': (optional),
                  'port': (optional),
                  'keys': [(optional)],
                  }, ...]""", default=[]),
    ct.Cfg('roles', ct.JSONList(),
           help="Node roles managed by underlay in the environment",
           default=[ext.UNDERLAY_NODE_ROLE.salt-master,
                    ext.UNDERLAY_NODE_ROLE.salt-minion, ]),
    ct.Cfg('nameservers', ct.JSONList(),
           help="IP addresses of DNS servers",
           default=[]),
    ct.Cfg('upstream_dns_servers', ct.JSONList(),
           help="IP addresses of upstream DNS servers (dnsmasq)",
           default=[]),
    ct.Cfg('lvm', ct.JSONDict(),
           help="LVM settings for Underlay", default={}),
]

# Deploy options for a new TCPCloud deployment
tcp_deploy_opts = [
    ct.Cfg('reclass_settings', ct.JSONDict(),
           help="", default={}),
]


# Access credentials to a ready TCP cluster
tcp_opts = [
    ct.Cfg('tcp_host', ct.IPAddress(),
           help="", default='0.0.0.0'),
]


os_deploy_opts = [
    # ct.Cfg('stacklight_enable', ct.Boolean(),
    #        help="", default=False),
]

os_opts = [
    ct.Cfg('keystone_endpoint', ct.String(),
           help="", default=''),
]


_group_opts = [
    ('hardware', hardware_opts),
    ('underlay', underlay_opts),
    ('tcp_deploy', tcp_deploy_opts),
    ('tcp', tcp_opts),
    ('os_deploy', os_deploy_opts),
    ('os', os_opts),
]


def register_opts(config):
    config.register_group(cfg.OptGroup(name='hardware',
                          title="Hardware settings", help=""))
    config.register_opts(group='hardware', opts=hardware_opts)

    config.register_group(cfg.OptGroup(name='underlay',
                          title="Underlay configuration", help=""))
    config.register_opts(group='underlay', opts=underlay_opts)

    config.register_group(cfg.OptGroup(name='tcp_deploy',
                          title="tcp deploy configuration", help=""))
    config.register_opts(group='tcp_deploy', opts=tcp_deploy_opts)

    config.register_group(cfg.OptGroup(name='tcp',
                          title="tcp config and credentials", help=""))
    config.register_opts(group='tcp', opts=tcp_opts)

    config.register_group(cfg.OptGroup(name='os',
                          title="Openstack config and credentials", help=""))
    config.register_opts(group='os', opts=os_opts)
    config.register_group(
        cfg.OptGroup(name='os_deploy',
                     title="Openstack deploy config and credentials",
                     help=""))
    config.register_opts(group='os_deploy', opts=os_deploy_opts)
    return config


def load_config(config_files):
    config = cfg.CONF
    register_opts(config)
    config(args=[], default_config_files=config_files)
    return config


def reload_snapshot_config(config, test_config_path):
    """Reset config to the state from test_config file"""
    config(args=[], default_config_files=[test_config_path])
    return config


def list_opts():
    """Return a list of oslo.config options available in the tcp_tests.
    """
    return [(group, copy.deepcopy(opts)) for group, opts in _group_opts]


def list_current_opts(config):
    """Return a list of oslo.config options available in the tcp_tests.
    """
    result_opts = []
    for group, opts in _group_opts:
        current_opts = copy.deepcopy(opts)
        for opt in current_opts:
            if hasattr(config, group):
                if hasattr(config[group], opt.name):
                    opt.default = getattr(config[group], opt.name)
        result_opts.append((group, current_opts))
    return result_opts


def save_config(config, snapshot_name, env_name=None):
    if env_name is None:
        env_name = 'config'
    test_config_path = os.path.join(
        settings.LOGS_DIR, '{0}_{1}.ini'.format(env_name, snapshot_name))

    with open(test_config_path, 'w') as output_file:
        formatter = generator._OptFormatter(output_file=output_file)
        for group, opts in list_current_opts(config):
            formatter.format_group(group)
            for opt in opts:
                formatter.format(opt, group, minimal=True)
                formatter.write('\n')
            formatter.write('\n')
