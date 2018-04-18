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

print("\n" + "-" * 10 + " Initialize oslo.config variables with defaults"
      " from environment" + "-" * 10)

_default_conf = pkg_resources.resource_filename(
    __name__, 'templates/{0}/underlay.yaml'.format(settings.LAB_CONFIG_NAME))

_default_salt_steps = pkg_resources.resource_filename(
    __name__, 'templates/{0}/salt.yaml'.format(settings.LAB_CONFIG_NAME))
_default_environment_template_dir = pkg_resources.resource_filename(
    __name__, 'environment/')
_default_templates_dir = pkg_resources.resource_filename(
    __name__, 'templates/')
_default_common_services_steps = pkg_resources.resource_filename(
    __name__,
    'templates/{0}/common-services.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_oss_steps = pkg_resources.resource_filename(
    __name__,
    'templates/{0}/oss.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_drivetrain_steps = pkg_resources.resource_filename(
    __name__,
    'templates/{0}/drivetrain.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_decapod_steps = pkg_resources.resource_filename(
    __name__,
    'templates/{0}/decapod.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_openstack_steps = pkg_resources.resource_filename(
    __name__, 'templates/{0}/openstack.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_opencontrail_prepare_tests_steps_path = \
    pkg_resources.resource_filename(
        __name__, 'templates/{0}/opencontrail.yaml'.format(
            settings.LAB_CONFIG_NAME))
_default_sl_prepare_tests_steps_path = pkg_resources.resource_filename(
    __name__, 'templates/{0}/sl.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_ceph_prepare_tests_steps_path = pkg_resources.resource_filename(
    __name__, 'templates/{0}/ceph.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_k8s_steps = pkg_resources.resource_filename(
    __name__, 'templates/{0}/k8s.yaml'.format(
        settings.LAB_CONFIG_NAME))
_default_net_mgm = os.environ.get("NET_MGMT", "admin-pool01")


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
                    ext.UNDERLAY_NODE_ROLES.salt_minion,
                    ext.UNDERLAY_NODE_ROLES.k8s_controller]),
    ct.Cfg('bootstrap_timeout', ct.Integer(),
           help="Timeout of waiting SSH for nodes with specified roles",
           default=600),
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
    ct.Cfg('ssh_keys', ct.JSONList(), default=[],
           help="SSH key pair(s) for root. If the option is left empty, "
                "then a key pair will be generated automatically"),
    ct.Cfg('ssh_key_file', ct.String(), default=os.path.abspath('./id_rsa'),
           help='Path (local) to file with private key authorized on nodes'),
    ct.Cfg('net_mgmt', ct.String(), default=_default_net_mgm)
]


salt_deploy_opts = [
    ct.Cfg('salt_steps_path', ct.String(),
           help="Path to YAML with steps to deploy salt",
           default=_default_salt_steps),
    ct.Cfg('environment_template_dir', ct.String(),
           help="Path to directory with Environment template and inventory",
           default=_default_environment_template_dir),
    ct.Cfg('templates_dir', ct.String(),
           help="Path to directory with templates",
           default=_default_templates_dir),
    ct.Cfg('salt_roles', ct.JSONList(),
           help="Node roles to install salt-minions and manage by salt",
           default=[ext.UNDERLAY_NODE_ROLES.salt_master,
                    ext.UNDERLAY_NODE_ROLES.salt_minion,
                    ext.UNDERLAY_NODE_ROLES.k8s_controller]),
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

oss_deploy_opts = [
    ct.Cfg('oss_steps_path', ct.String(),
           help="Path to YAML with steps to deploy OSS Tools",
           default=_default_oss_steps),
]

oss_opts = [
    ct.Cfg('oss_installed', ct.Boolean(),
           help="", default=False),
]

drivetrain_deploy_opts = [
    ct.Cfg('drivetrain_steps_path', ct.String(),
           help="Path to YAML with steps to deploy Drivetrain",
           default=_default_drivetrain_steps),
]

drivetrain_opts = [
    ct.Cfg('drivetrain_installed', ct.Boolean(),
           help="", default=False),
]

decapod_deploy_opts = [
    ct.Cfg('decapod_steps_path', ct.String(),
           help="Path to YAML with steps to deploy Ceph with Decapod",
           default=_default_decapod_steps),
]

decapod_opts = [
    ct.Cfg('decapod_installed', ct.Boolean(),
           help="", default=False),
]

openstack_deploy_opts = [
    ct.Cfg('openstack_steps_path', ct.String(),
           help="Path to YAML with steps to deploy openstack",
           default=_default_openstack_steps),
    ct.Cfg('horizon_host', ct.IPAddress(),
           help="", default='0.0.0.0'),
    ct.Cfg('horizon_port', ct.String(),
           help="", default='5000'),
    ct.Cfg('horizon_user', ct.String(),
           help="", default='admin'),
    ct.Cfg('horizon_password', ct.String(),
           help="", default='workshop'),
    ct.Cfg('horizon_check', ct.Boolean(),
           help="", default=True),
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
    ct.Cfg('docker_image_alertmanager', ct.String(),
           default='{0}/openstack-docker/alertmanager:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    ct.Cfg('docker_image_pushgateway', ct.String(),
           default='{0}/openstack-docker/pushgateway:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    ct.Cfg('docker_image_prometheus', ct.String(),
           default='{0}/openstack-docker/prometheus:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    ct.Cfg('docker_image_remote_agent', ct.String(),
           default='{0}/openstack-docker/telegraf:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    ct.Cfg('docker_image_remote_storage_adapter', ct.String(),
           default='{0}/openstack-docker/remote_storage_adapter:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    ct.Cfg('docker_image_prometheus_relay', ct.String(),
           default='{0}/openstack-docker/prometheus_relay:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    ct.Cfg('docker_image_grafana', ct.String(),
           default='{0}/mirantis/external/grafana:{1}'.format(
               settings.DOCKER_REGISTRY, settings.DOCKER_IMAGES_SL_TAG)),
    # SalesForce connection options for pushkin
    ct.Cfg('sfdc_sandbox_enabled', ct.String(), default='False'),
    ct.Cfg('sfdc_auth_url', ct.String(), default=''),
    ct.Cfg('sfdc_username', ct.String(), default=''),
    ct.Cfg('sfdc_password', ct.String(), default=''),
    ct.Cfg('sfdc_consumer_key', ct.String(), default=''),
    ct.Cfg('sfdc_consumer_secret', ct.String(), default=''),
    ct.Cfg('sfdc_organization_id', ct.String(), default=''),
]

sl_opts = [
    ct.Cfg('sl_installed', ct.Boolean(),
           help="", default=False),
    ct.Cfg('sl_version', ct.String(),
           help="StackLight version. Could be 1 or 2", default=''),
    ct.Cfg('sl_vip_host', ct.IPAddress(),
           help="Vip address for SL services", default='0.0.0.0'),
    ct.Cfg('sl_prometheus_port', ct.String(),
           help="Prometheus port", default='15010'),
    ct.Cfg('sl_prometheus_proto', ct.String(),
           help="Proemtheus protocol", default='http'),
]

ceph_deploy_opts = [
    ct.Cfg('ceph_steps_path', ct.String(),
           help="Path to YAML with steps to deploy sl",
           default=_default_ceph_prepare_tests_steps_path),
]

ceph_opts = [
    ct.Cfg('ceph_installed', ct.Boolean(),
           help="", default=False),
]

k8s_deploy_opts = [
    ct.Cfg('k8s_steps_path', ct.String(),
           help="Path to YAML with steps to deploy Kubernetes",
           default=_default_k8s_steps),
    ct.Cfg('kubernetes_admin_user', ct.String(), default='admin'),
    ct.Cfg('kubernetes_admin_password', ct.String(),
           default='sbPfel23ZigJF3Bm'),
    ct.Cfg('kubernetes_docker_package', ct.String(), default=''),
    ct.Cfg('kubernetes_hyperkube_image', ct.String(),
           default='{}/mirantis/kubernetes/hyperkube-amd64:v1.8.11-9'.format(
               settings.DOCKER_REGISTRY)),
    ct.Cfg('kubernetes_calico_image', ct.String(),
           default='{}/mirantis/projectcalico/calico/node:latest'.format(
               settings.DOCKER_REGISTRY)),
    ct.Cfg('kubernetes_calicoctl_image', ct.String(),
           default='{}/mirantis/projectcalico/calico/ctl:latest'.format(
               settings.DOCKER_REGISTRY)),
    ct.Cfg('kubernetes_calico_cni_image', ct.String(),
           default='{}/mirantis/projectcalico/calico/cni:latest'.format(
               settings.DOCKER_REGISTRY)),
    ct.Cfg('kubernetes_netchecker_enabled', ct.Boolean(),
           help="", default=True),
    ct.Cfg('kubernetes_netchecker_agent_image', ct.String(),
           default='mirantis/k8s-netchecker-agent:latest'),
    ct.Cfg('kubernetes_netchecker_server_image', ct.String(),
           default='mirantis/k8s-netchecker-server:latest'),
    ct.Cfg('kubernetes_calico_policy_enabled', ct.Boolean(),
           help="", default=False),
    ct.Cfg('kubernetes_calico_policy_image', ct.String(),
           default='calico/kube-policy-controller:v0.5.4'),
    ct.Cfg('kubernetes_helm_enabled', ct.Boolean(),
           help="", default=False),
    ct.Cfg('kubernetes_virtlet_enabled', ct.Boolean(),
           help="", default=False),
    ct.Cfg('kubernetes_virtlet_image', ct.String(),
           help="", default='mirantis/virtlet:v0.8.0'),
    ct.Cfg('kubernetes_externaldns_enabled', ct.Boolean(),
           help="", default=False),
    ct.Cfg('kubernetes_externaldns_image', ct.String(),
           help="", default='mirantis/external-dns:latest'),
    ct.Cfg('kubernetes_externaldns_provider', ct.String(),
           help="", default='coredns'),
    ct.Cfg('kubernetes_coredns_enabled', ct.Boolean(),
           help="", default=False),
    ct.Cfg('kubelet_fail_on_swap', ct.Boolean(),
           help="", default=False)
]

k8s_opts = [
    ct.Cfg('k8s_installed', ct.Boolean(),
           help="", default=False),
    ct.Cfg('kube_host', ct.IPAddress(),
           help="", default='0.0.0.0'),
    ct.Cfg('kube_apiserver_port', ct.Integer(),
           help="", default=443),
    ct.Cfg("k8s_conformance_run", ct.Boolean(),
           default=False),
    ct.Cfg("run_extended_virtlet_conformance", ct.Boolean(),
           default=False),
    ct.Cfg('k8s_conformance_image', ct.String(),
           default='docker-prod-virtual.docker.mirantis.net/mirantis/'
                   'kubernetes/k8s-conformance:v1.8.11-9')
]

_group_opts = [
    ('hardware', hardware_opts),
    ('underlay', underlay_opts),
    ('salt_deploy', salt_deploy_opts),
    ('salt', salt_opts),
    ('common_services_deploy', common_services_deploy_opts),
    ('common_services', common_services_opts),
    ('oss_deploy', oss_deploy_opts),
    ('oss', oss_opts),
    ('drivetrain_deploy', drivetrain_deploy_opts),
    ('drivetrain', drivetrain_opts),
    ('decapod_deploy', decapod_deploy_opts),
    ('decapod', decapod_opts),
    ('openstack_deploy', openstack_deploy_opts),
    ('openstack', openstack_opts),
    ('opencontrail', opencontrail_opts),
    ('stack_light', sl_opts),
    ('sl_deploy', sl_deploy_opts),
    ('ceph', ceph_opts),
    ('ceph_deploy', ceph_deploy_opts),
    ('k8s_deploy', k8s_deploy_opts),
    ('k8s', k8s_opts),
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

    config.register_group(cfg.OptGroup(name='oss',
                          title="Operational Support System Tools", help=""))
    config.register_opts(group='oss', opts=oss_opts)

    config.register_group(cfg.OptGroup(name='oss_deploy',
                          title="OSS deploy config", help=""))
    config.register_opts(group='oss_deploy',
                         opts=oss_deploy_opts)

    config.register_group(cfg.OptGroup(name='drivetrain',
                          title="Drivetrain Tools", help=""))
    config.register_opts(group='drivetrain', opts=drivetrain_opts)

    config.register_group(cfg.OptGroup(name='drivetrain_deploy',
                          title="Drivetrain deploy config", help=""))
    config.register_opts(group='drivetrain_deploy',
                         opts=drivetrain_deploy_opts)

    config.register_group(cfg.OptGroup(name='decapod',
                          title="Decapod options for Ceph", help=""))
    config.register_opts(group='decapod', opts=decapod_opts)

    config.register_group(cfg.OptGroup(name='decapod_deploy',
                          title="Decapod deploy config", help=""))
    config.register_opts(group='decapod_deploy',
                         opts=decapod_deploy_opts)

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
    config.register_group(
        cfg.OptGroup(name='stack_light',
                     title="StackLight config and credentials", help=""))
    config.register_opts(group='stack_light', opts=sl_opts)
    config.register_group(
        cfg.OptGroup(name='sl_deploy',
                     title="SL deploy config and credentials",
                     help=""))
    config.register_opts(group='sl_deploy', opts=sl_deploy_opts)

    config.register_group(cfg.OptGroup(name='k8s_deploy',
                                       title="K8s deploy configuration"))
    config.register_opts(group='k8s_deploy', opts=k8s_deploy_opts)

    config.register_group(cfg.OptGroup(name='k8s',
                                       title="K8s config and credentials"))
    config.register_opts(group='k8s', opts=k8s_opts)
    config.register_group(cfg.OptGroup(name='ceph',
                                       title="ceph config", help=""))
    config.register_opts(group='ceph', opts=ceph_opts)

    config.register_group(
        cfg.OptGroup(name='ceph_deploy',
                     title="Ceph deploy config ",
                     help=""))
    config.register_opts(group='ceph_deploy', opts=ceph_deploy_opts)

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
