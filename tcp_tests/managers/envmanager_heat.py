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
import netaddr
import yaml

from devops.helpers import helpers
from devops.helpers.helpers import ssh_client
from retry import retry

from django.utils import functional

from heatclient import client as heatclient
from heatclient import exc as heat_exceptions
from heatclient.common import template_utils
from keystoneauth1.identity import v3 as keystone_v3
from keystoneauth1 import session as keystone_session

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from oslo_config import cfg
from paramiko.ssh_exception import (
    AuthenticationException,
    BadAuthenticationType)

from tcp_tests import settings
from tcp_tests import settings_oslo
from tcp_tests.helpers import exceptions
from tcp_tests import logger

LOG = logger.logger

EXPECTED_STACK_STATUS = "CREATE_COMPLETE"
BAD_STACK_STATUSES = ["CREATE_FAILED"]

# Disable multiple notifications like:
# "InsecureRequestWarning: Unverified HTTPS request is being made."
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class EnvironmentManagerHeat(object):
    """Class-helper for creating VMs via devops environments"""

    __config = None

    # Do not use self.__heatclient directly! Use properties
    # for necessary resources with catching HTTPUnauthorized exception
    __heatclient = None

    def __init__(self, config=None):
        """Create/connect to the Heat stack with test environment

        :param config: oslo.config object
        :param config.hardware.heat_version: Heat version
        :param config.hardware.os_auth_url: OS auth URL to access heat
        :param config.hardware.os_username: OS username
        :param config.hardware.os_password: OS password
        :param config.hardware.os_project_name: OS tenant name
        """
        self.__config = config

        if not self.__config.hardware.heat_stack_name:
            self.__config.hardware.heat_stack_name = settings.ENV_NAME

        self.__init_heatclient()

        try:
            stack_status = self._current_stack.stack_status
            if stack_status != EXPECTED_STACK_STATUS:
                raise exceptions.EnvironmentWrongStatus(
                    self.__config.hardware.heat_stack_name,
                    EXPECTED_STACK_STATUS,
                    stack_status
                )
            LOG.info("Heat stack '{0}' already exists".format(
                self.__config.hardware.heat_stack_name))
        except heat_exceptions.HTTPNotFound:
            self._create_environment()
            LOG.info("Heat stack '{0}' created".format(
                self.__config.hardware.heat_stack_name))

        self.set_address_pools_config()
        self.set_dhcp_ranges_config()

    @functional.cached_property
    def _keystone_session(self):
        keystone_auth = keystone_v3.Password(
            auth_url=settings.OS_AUTH_URL,
            username=settings.OS_USERNAME,
            password=settings.OS_PASSWORD,
            project_name=settings.OS_PROJECT_NAME,
            user_domain_name='Default',
            project_domain_name='Default')
        return keystone_session.Session(auth=keystone_auth, verify=False)

    def __init_heatclient(self):
        token = self._keystone_session.get_token()
        endpoint_url = self._keystone_session.get_endpoint(
            service_type='orchestration', endpoint_type='publicURL')
        self.__heatclient = heatclient.Client(
            version=settings.OS_HEAT_VERSION, endpoint=endpoint_url,
            token=token, insecure=True)

    @property
    def _current_stack(self):
        return self.__stacks.get(
            self.__config.hardware.heat_stack_name)

    @property
    def __stacks(self):
        try:
            return self.__heatclient.stacks
        except heat_exceptions.HTTPUnauthorized:
            LOG.warning("Authorization token outdated, refreshing")
            self.__init_heatclient()
            return self.__heatclient.stacks

    @property
    def __resources(self):
        try:
            return self.__heatclient.resources
        except heat_exceptions.HTTPUnauthorized:
            LOG.warning("Authorization token outdated, refreshing")
            self.__init_heatclient()
            return self.__heatclient.resources

    def _get_resources_by_type(self, resource_type):
        res = []
        for item in self.__resources.list(
                self.__config.hardware.heat_stack_name):
            if item.resource_type == resource_type:
                resource = self.__resources.get(
                    self.__config.hardware.heat_stack_name,
                    item.resource_name)
                res.append(resource)
        return res

    @functional.cached_property
    def _nodes(self):
        """Get list of nodenames from heat

        Returns list of dicts.
        Example:
        - name: cfg01
          roles:
          - salt_master
          addresses:  # Optional. May be an empty dict
            admin-pool01: p.p.p.202
        - name: ctl01
          roles:
          - salt_minion
          - openstack_controller
          - openstack_messaging
          - openstack_database
          addresses: {} # Optional. May be an empty dict

        'name': taken from heat template resource's ['name'] parameter
        'roles': a list taken from resource's ['metadata']['roles'] parameter
        """
        address_pools = self._address_pools
        nodes = []
        for heat_node in self._get_resources_by_type("OS::Nova::Server"):
            # addresses will have the following dict structure:
            #   {'admin-pool01': <floating_ip1>,
            #    'private-pool01': <floating_ip2>,
            #    'external-pool01': <floating_ip3>
            #   }
            # , where key is one of roles from OS::Neutron::Subnet,
            # and value is a floating IP associated to the fixed IP
            # in this subnet (if exists).
            # If no floating IPs associated to the server,
            # then addresses will be an empty list.
            addresses = {}
            for network in heat_node.attributes['addresses']:
                fixed = None
                floating = None
                for address in heat_node.attributes['addresses'][network]:
                    addr_type = address['OS-EXT-IPS:type']
                    if addr_type == 'fixed':
                        fixed = address['addr']
                    elif addr_type == 'floating':
                        floating = address['addr']
                    else:
                        LOG.error("Unexpected OS-EXT-IPS:type={0} "
                                  "in node '{1}' for network '{2}'"
                                  .format(addr_type,
                                          heat_node.attributes['name'],
                                          network))
                if fixed is None or floating is None:
                    LOG.error("Unable to determine the correct IP address "
                              "in node '{0}' for network '{1}'"
                              .format(heat_node.attributes['name'], network))
                    continue
                # Check which address pool has the fixed address, and set
                # the floating address as the access to this address pool.
                for address_pool in address_pools:
                    pool_net = netaddr.IPNetwork(address_pool['cidr'])
                    if fixed in pool_net:
                        for role in address_pool['roles']:
                            addresses[role] = floating

            nodes.append({
                'name': heat_node.attributes['name'],
                'roles': yaml.load(heat_node.attributes['metadata']['roles']),
                'addresses': addresses,
            })
        return nodes

    @functional.cached_property
    def _address_pools(self):
        """Get address pools from subnets OS::Neutron::Subnet

        Returns list of dicts.
        Example:
        - roles:
          - admin-pool01
          cidr: x.x.x.x/y
          start: x.x.x.2
          end: x.x.x.254
          gateway: x.x.x.1 # or None
        """
        pools = []
        for heat_subnet in self._get_resources_by_type("OS::Neutron::Subnet"):
            pools.append({
                'roles': heat_subnet.attributes['tags'],
                'cidr': heat_subnet.attributes['cidr'],
                'gateway': heat_subnet.attributes['gateway_ip'],
                'start': heat_subnet.attributes[
                    'allocation_pools'][0]['start'],
                'end': heat_subnet.attributes['allocation_pools'][0]['end'],
            })
        return pools

    def _get_nodes_by_roles(self, roles=None):
        nodes = []
        if roles is None:
            return self._nodes

        for node in self._nodes:
            if set(node['roles']).intersection(set(roles)):
                nodes.append(node)
        return nodes

    def get_ssh_data(self, roles=None):
        """Generate ssh config for Underlay

        :param roles: list of strings
        """
        if roles is None:
            raise Exception("No roles specified for the environment!")

        config_ssh = []
        for d_node in self._get_nodes_by_roles(roles=roles):
            for pool_name in d_node['addresses']:
                ssh_data = {
                    'node_name': d_node['name'],
                    'minion_id': d_node['name'],
                    'roles': d_node['roles'],
                    'address_pool': pool_name,
                    'host': d_node['addresses'][pool_name],
                    'login': settings.SSH_NODE_CREDENTIALS['login'],
                    'password': settings.SSH_NODE_CREDENTIALS['password'],
                    'keys': [k['private']
                             for k in self.__config.underlay.ssh_keys]
                }
            config_ssh.append(ssh_data)
        return config_ssh

    def _get_resources_with_wrong_status(self):
        res = []
        for item in self.__resources.list(
                self.__config.hardware.heat_stack_name):
            if item.resource_status in BAD_STACK_STATUSES:
                res.append({
                    'resource_name': item.resource_name,
                    'resource_status': item.resource_status,
                    'resource_status_reason': item.resource_status_reason,
                    'resource_type': item.resource_type
                })
        wrong_resources = '\n'.join([
            "*** Heat stack resource '{0}' ({1}) has wrong status '{2}': {3}"
            .format(item['resource_name'],
                    item['resource_type'],
                    item['resource_status'],
                    item['resource_status_reason'])
            for item in res
        ])
        return wrong_resources

    def wait_of_stack_status(self, status, delay=30, tries=60):

        @retry(exceptions.EnvironmentWrongStatus, delay=delay, tries=tries)
        def wait():
            st = self._current_stack.stack_status
            if st == status:
                return
            elif st in BAD_STACK_STATUSES:
                wrong_resources = self._get_resources_with_wrong_status()
                raise exceptions.EnvironmentBadStatus(
                    self.__config.hardware.heat_stack_name,
                    status,
                    st,
                    wrong_resources
                )
            else:
                LOG.info("Stack {0} status: {1}".format(
                    self.__config.hardware.heat_stack_name, st))
                raise exceptions.EnvironmentWrongStatus(
                    self.__config.hardware.heat_stack_name,
                    status,
                    st
                )
        LOG.info("Waiting for stack '{0}' status <{1}>".format(
            self.__config.hardware.heat_stack_name, status))
        wait()

    def revert_snapshot(self, name):
        """Revert snapshot by name

        - Revert the heat snapshot in the environment
        - Try to reload 'config' object from a file 'config_<name>.ini'
          If the file not found, then pass with defaults.
        - Set <name> as the current state of the environment after reload

        :param name: string
        """
        LOG.info("Reading INI config (without reverting env to snapshot) "
                 "named '{0}'".format(name))

        try:
            test_config_path = self._get_snapshot_config_name(name)
            settings_oslo.reload_snapshot_config(self.__config,
                                                 test_config_path)
        except cfg.ConfigFilesNotFoundError as conf_err:
            LOG.error("Config file(s) {0} not found!".format(
                conf_err.config_files))

        self.__config.hardware.current_snapshot = name

    def create_snapshot(self, name, *args, **kwargs):
        """Create named snapshot of current env.

        - Create a snapshot for the environment
        - Save 'config' object to a file 'config_<name>.ini'

        :name: string
        """
        LOG.info("Store INI config (without env snapshot) named '{0}'"
                 .format(name))
        self.__config.hardware.current_snapshot = name
        settings_oslo.save_config(self.__config,
                                  name,
                                  self.__config.hardware.heat_stack_name)

    def _get_snapshot_config_name(self, snapshot_name):
        """Get config name for the environment"""
        env_name = self.__config.hardware.heat_stack_name
        if env_name is None:
            env_name = 'config'
        test_config_path = os.path.join(
            settings.LOGS_DIR, '{0}_{1}.ini'.format(env_name, snapshot_name))
        return test_config_path

    def has_snapshot(self, name):
        # Heat doesn't support live snapshots, so just
        # check if an INI file was created for this environment,
        # assuming that the environment has the configuration
        # described in this INI.
        return self.has_snapshot_config(name)

    def has_snapshot_config(self, name):
        test_config_path = self._get_snapshot_config_name(name)
        return os.path.isfile(test_config_path)

    def start(self, underlay_node_roles, timeout=480):
        """Start environment"""
        LOG.warning("HEAT Manager doesn't support start environment feature. "
                    "Waiting for finish the bootstrap process on the nodes "
                    "with accessible SSH")

        check_cloudinit_started = '[ -f /is_cloud_init_started ]'
        check_cloudinit_finished = ('[ -f /is_cloud_init_finished ] || '
                                    '[ -f /var/log/mcp/.bootstrap_done ]')
        check_cloudinit_failed = 'cat /is_cloud_init_failed'
        passed = {}
        for node in self._get_nodes_by_roles(roles=underlay_node_roles):
            LOG.info("Waiting for SSH on node '{0}' / {1} ...".format(
                node['name'], self.node_ip(node)))

            def _ssh_check(host,
                           port,
                           username=settings.SSH_NODE_CREDENTIALS['login'],
                           password=settings.SSH_NODE_CREDENTIALS['password'],
                           timeout=0):
                try:
                    ssh = ssh_client.SSHClient(
                        host=host, port=port,
                        auth=ssh_client.SSHAuth(
                            username=username,
                            password=password))

                    # If '/is_cloud_init_started' exists, then wait for
                    # the flag /is_cloud_init_finished
                    if ssh.execute(check_cloudinit_started)['exit_code'] == 0:
                        result = ssh.execute(check_cloudinit_failed)
                        if result['exit_code'] == 0:
                            raise exceptions.EnvironmentNodeIsNotStarted(
                                "{0}:{1}".format(host, port),
                                result.stdout_str)

                        status = ssh.execute(
                            check_cloudinit_finished)['exit_code'] == 0
                    # Else, just wait for SSH
                    else:
                        status = ssh.execute('echo ok')['exit_code'] == 0
                    return status

                except (AuthenticationException, BadAuthenticationType):
                    return True
                except Exception:
                    return False

            def _ssh_wait(host,
                          port,
                          username=settings.SSH_NODE_CREDENTIALS['login'],
                          password=settings.SSH_NODE_CREDENTIALS['password'],
                          timeout=0):

                if host in passed and passed[host] >= 2:
                    # host already passed the check
                    return True

                for node in self._get_nodes_by_roles(
                        roles=underlay_node_roles):
                    ip = self.node_ip(node)
                    if ip not in passed:
                        passed[ip] = 0
                    if _ssh_check(ip, port):
                        passed[ip] += 1
                    else:
                        passed[ip] = 0

            helpers.wait(
                lambda: _ssh_wait(self.node_ip(node), 22),
                timeout=timeout,
                timeout_msg="Node '{}' didn't open SSH in {} sec".format(
                    node['name'], timeout
                )
            )
        LOG.info('Heat stack "{0}" ready'
                 .format(self.__config.hardware.heat_stack_name))

    def _create_environment(self):
        tpl_files, template = template_utils.get_template_contents(
            self.__config.hardware.heat_conf_path)
        env_files_list = []
        env_files, env = (
            template_utils.process_multiple_environments_and_files(
                env_paths=[self.__config.hardware.heat_env_path],
                env_list_tracker=env_files_list))

        fields = {
            'stack_name': self.__config.hardware.heat_stack_name,
            'template': template,
            'files': dict(list(tpl_files.items()) + list(env_files.items())),
            'environment': env,
        }

        if env_files_list:
            fields['environment_files'] = env_files_list

        self.__stacks.create(**fields)
        self.wait_of_stack_status(EXPECTED_STACK_STATUS)
        LOG.info("Stack '{0}' created"
                 .format(self.__config.hardware.heat_stack_name))

    def stop(self):
        """Stop environment"""
        LOG.warning("HEAT Manager doesn't support stop environment feature")
        pass

# TODO(ddmitriev): add all Environment methods
    @staticmethod
    def node_ip(node, address_pool_name='admin-pool01'):
        """Determine node's IP

        :param node: a dict element from the self._nodes
        :return: string
        """
        if address_pool_name in node['addresses']:
            addr = node['addresses'][address_pool_name]
            LOG.debug('{0} IP= {1}'.format(node['name'], addr))
            return addr
        else:
            raise exceptions.EnvironmentNodeAccessError(
                node['name'],
                "No addresses available for the subnet {0}"
                .format(address_pool_name))

    def set_address_pools_config(self):
        """Store address pools CIDRs in config object"""
        for ap in self._address_pools:
            for role in ap['roles']:
                self.__config.underlay.address_pools[role] = ap['cidr']

    def set_dhcp_ranges_config(self):
        """Store DHCP ranges in config object"""
        for ap in self._address_pools:
            for role in ap['roles']:
                self.__config.underlay.dhcp_ranges[role] = {
                    "cidr": ap['cidr'],
                    "start": ap['start'],
                    "end": ap['end'],
                    "gateway": ap['gateway'],
                }

    def wait_for_node_state(self, node_name, state, timeout):
        raise NotImplementedError()

    def warm_shutdown_nodes(self, underlay, nodes_prefix, timeout=600):
        raise NotImplementedError()

    def warm_restart_nodes(self, underlay, nodes_prefix, timeout=600):
        raise NotImplementedError()

    @property
    def slave_nodes(self):
        raise NotImplementedError()
