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

print ("\n" + "-" * 10 + " Initialize oslo.config variables with defaults"
       " from environment" + "-" * 10)

_default_conf = pkg_resources.resource_filename(
    __name__, 'templates/{0}/underlay.yaml'.format(settings.LAB_CONFIG_NAME))

_default_salt_steps = pkg_resources.resource_filename(
    __name__, 'templates/{0}/salt.yaml'.format(settings.LAB_CONFIG_NAME))
_default_common_services_steps = pkg_resources.resource_filename(
    __name__,
    'templates/{0}/common-services.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_openstack_steps = pkg_resources.resource_filename(
    __name__, 'templates/{0}/openstack.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_opencontrail_prepare_tests_steps_path = pkg_resources.resource_filename(
    __name__, 'templates/{0}/opencontrail.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_sl_prepare_tests_steps_path = pkg_resources.resource_filename(
    __name__, 'templates/{0}/sl.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_virtlet_prepare_tests_steps_path = pkg_resources.resource_filename(
    __name__, 'templates/{0}/virtlet.yaml'.format(
        settings.LAB_CONFIG_NAME))

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
                  'roles': ['salt-master', 'salt-minion', ],
                  'host': hostname,
                  'login': login,
                  'password': password,
                  'address_pool': (optional),
                  'port': (optional),
                  'keys': [(optional)],
                  }, ...]""", default=[]),
    ct.Cfg('roles', ct.JSONList(),
           help="Node roles managed by underlay in the environment",
           default=[ext.UNDERLAY_NODE_ROLES.salt_master,
                    ext.UNDERLAY_NODE_ROLES.salt_minion, ]),
    ct.Cfg('bootstrap_timeout', ct.Integer(),
           help="Timeout of waiting SSH for nodes with specified roles",
           default=480),
    ct.Cfg('nameservers', ct.JSONList(),
           help="IP addresses of DNS servers",
           default=[]),
    ct.Cfg('upstream_dns_servers', ct.JSONList(),
           help="IP addresses of upstream DNS servers (dnsmasq)",
           default=[]),
    ct.Cfg('lvm', ct.JSONDict(),
           help="LVM settings for Underlay", default={}),
    ct.Cfg('address_pools', ct.JSONDict(),
           help="""Address pools (dynamically) allocated for the environment.
                   May be used to determine CIDR for a specific network from
                   tests or during the deployment process.
                   {'pool_name1': '<cidr>', 'pool_name2': '<cidr>', ...}""",
           default={}),
]


salt_deploy_opts = [
    ct.Cfg('salt_steps_path', ct.String(),
           help="Path to YAML with steps to deploy salt",
           default=_default_salt_steps),
]
salt_opts = [
    ct.Cfg('salt_master_host', ct.IPAddress(),
           help="", default='0.0.0.0'),
    ct.Cfg('salt_master_port', ct.String(),
           help="", default='6969'),
]

common_services_deploy_opts = [
    ct.Cfg('common_services_steps_path', ct.String(),
           help="Path to YAML with steps to deploy common services",
           default=_default_common_services_steps),
]

common_services_opts = [
    ct.Cfg('common_services_installed', ct.Boolean(),
           help="", default=False),
]

openstack_deploy_opts = [
    ct.Cfg('openstack_steps_path', ct.String(),
           help="Path to YAML with steps to deploy openstack",
           default=_default_openstack_steps),
]
openstack_opts = [
    ct.Cfg('openstack_installed', ct.Boolean(),
           help="", default=False),
    ct.Cfg('openstack_keystone_endpoint', ct.String(),
           help="", default=''),
]

opencontrail_opts = [
    ct.Cfg('opencontrail_tags', ct.String(),
           help="", default=''),
    ct.Cfg('opencontrail_features', ct.String(),
           help="", default=''),
    ct.Cfg('opencontrail_prepare_tests_steps_path', ct.String(),
           help="Path to YAML with steps to prepare contrail-tests",
           default=_default_opencontrail_prepare_tests_steps_path),
]

sl_deploy_opts = [
    ct.Cfg('sl_steps_path', ct.String(),
           help="Path to YAML with steps to deploy sl",
           default=_default_sl_prepare_tests_steps_path),
]
sl_opts = [
    ct.Cfg('sl_installed', ct.Boolean(),
           help="", default=False),
]

virtlet_deploy_opts = [
    ct.Cfg('virtlet_steps_path', ct.String(),
           help="Path to YAML with steps to deploy virtlet",
           default=_default_virtlet_prepare_tests_steps_path)
]

virtlet_opts = [
    ct.Cfg('virtlet_installed', ct.Boolean(),
           help="", default=False),
]

_group_opts = [
    ('hardware', hardware_opts),
    ('underlay', underlay_opts),
    ('salt_deploy', salt_deploy_opts),
    ('salt', salt_opts),
    ('common_services_deploy', common_services_deploy_opts),
    ('common_services', common_services_opts),
    ('openstack_deploy', openstack_deploy_opts),
    ('openstack', openstack_opts),
    ('opencontrail', opencontrail_opts),
    ('stack_light', sl_opts),
    ('sl_deploy', sl_deploy_opts),
    ('virtlet_deploy', virtlet_deploy_opts),
    ('virtlet', virtlet_opts),
]


def register_opts(config):
    config.register_group(cfg.OptGroup(name='hardware',
                          title="Hardware settings", help=""))
    config.register_opts(group='hardware', opts=hardware_opts)

    config.register_group(cfg.OptGroup(name='underlay',
                          title="Underlay configuration", help=""))
    config.register_opts(group='underlay', opts=underlay_opts)

    config.register_group(cfg.OptGroup(name='salt_deploy',
                          title="salt deploy configuration", help=""))
    config.register_opts(group='salt_deploy', opts=salt_deploy_opts)

    config.register_group(cfg.OptGroup(name='salt',
                          title="salt config and credentials", help=""))
    config.register_opts(group='salt', opts=salt_opts)

    config.register_group(cfg.OptGroup(name='common_services',
                          title="Common services for Openstack", help=""))
    config.register_opts(group='common_services', opts=common_services_opts)

    config.register_group(
        cfg.OptGroup(name='common_services_deploy',
                     title="Common services for Openstack deploy config",
                     help=""))
    config.register_opts(group='common_services_deploy',
                         opts=common_services_deploy_opts)

    config.register_group(cfg.OptGroup(name='openstack',
                          title="Openstack config and credentials", help=""))
    config.register_opts(group='openstack', opts=openstack_opts)

    config.register_group(
        cfg.OptGroup(name='openstack_deploy',
                     title="Openstack deploy config and credentials",
                     help=""))
    config.register_opts(group='openstack_deploy', opts=openstack_deploy_opts)

    config.register_group(cfg.OptGroup(name='opencontrail',
                          title="Options for Juniper contrail-tests", help=""))
    config.register_opts(group='opencontrail', opts=opencontrail_opts)
    config.register_group(cfg.OptGroup(name='stack_light',
                                       title="StackLight config and credentials", help=""))
    config.register_opts(group='stack_light', opts=sl_opts)
    config.register_group(
        cfg.OptGroup(name='sl_deploy',
                 title="SL deploy config and credentials",
                 help=""))
    config.register_opts(group='sl_deploy', opts=sl_deploy_opts)
    config.register_group(cfg.OptGroup(name='virtlet_deploy',
                                       title='Virtlet deploy config', help=""))
    config.register_opts(group='virtlet_deploy', opts=virtlet_deploy_opts)
    config.register_group(cfg.OptGroup(name='virtlet',
                                       title='Virtlet config', help=""))
    config.register_opts(group='virtlet', opts=virtlet_opts)
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
