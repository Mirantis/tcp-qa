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
import requests

from tcp_tests.managers.execute_commands import ExecuteCommandsMixin
from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class OpenstackManager(ExecuteCommandsMixin):
    """docstring for OpenstackManager"""

    __config = None
    __underlay = None
    __hardware = None

    def __init__(self, config, underlay,  hardware, salt):
        self.__config = config
        self.__underlay = underlay
        self.__hardware = hardware
        self._salt = salt
        super(OpenstackManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install OpenStack services')
        self.__config.openstack.openstack_installed = True
        h_data = self.get_horizon_data()
        self.__config.openstack.horizon_host = h_data['horizon_host']
        self.__config.openstack.horizon_port = h_data['horizon_port']
        self.__config.openstack.horizon_user = h_data['horizon_user']
        self.__config.openstack.horizon_password = h_data['horizon_password']
        self.auth_in_horizon(
            h_data['horizon_host'],
            h_data['horizon_port'],
            h_data['horizon_user'],
            h_data['horizon_password'])

    def get_horizon_data(self):
        horizon_data = {}
        tgt = 'I@nginx:server and not cfg*'
        pillar_host = ('nginx:server:site:nginx_ssl_redirect'
                       '_openstack_web:host:name')
        pillar_port = ('nginx:server:site:nginx_ssl_redirect'
                       '_openstack_web:host:port')
        hosts = self._salt.get_pillar(tgt=tgt, pillar=pillar_host)
        host = set([ip for item in hosts for node, ip
                    in item.items() if ip])
        if host:
            host = host.pop()
        ports = self._salt.get_pillar(tgt=tgt, pillar=pillar_port)

        port = set([port for item in ports for node, port
                    in item.items() if port])
        if port:
            port = port.pop()
        tgt = 'I@keystone:server and ctl01*'
        pillar_user = 'keystone:server:admin_name'
        pillar_password = 'keystone:server:admin_password'
        users = self._salt.get_pillar(tgt=tgt, pillar=pillar_user)
        user = set([user for item in users for node, user
                    in item.items() if user])
        if user:
            user = user.pop()
        passwords = self._salt.get_pillar(tgt=tgt, pillar=pillar_password)
        pwd = set([pwd for item in passwords for node, pwd
                   in item.items() if pwd])
        if pwd:
            pwd = pwd.pop()
        horizon_data.update({'horizon_host': host})
        horizon_data.update({'horizon_port': port})
        horizon_data.update({'horizon_user': user})
        horizon_data.update({'horizon_password': pwd})
        LOG.info("Data from pillars {}".format(horizon_data))

        return horizon_data

    def run_tempest(
            self,
            target='gtw01', pattern=None,
            conf_name='lvm_mcp.conf',
            registry=None):
        if not registry:
            registry = ('{0}/{1}'.format(settings.DOCKER_REGISTRY,
                                         settings.DOCKER_NAME))
        target_name = [node_name for node_name
                       in self.__underlay.node_names() if target in node_name]

        cmd = ("apt-get -y install docker.io")
        with self.__underlay.remote(node_name=target_name[0]) as node_remote:
            result = node_remote.execute(cmd, verbose=True)

        cmd_iptables = "iptables --policy FORWARD ACCEPT"
        with self.__underlay.remote(node_name=target_name[0]) as node_remote:
            result = node_remote.execute(cmd_iptables, verbose=True)

        with self.__underlay.remote(
                host=self.__config.salt.salt_master_host) as node_remote:
            result = node_remote.execute(
                ("scp ctl01:/root/keystonercv3 /root;"
                 "scp /root/keystonercv3 gtw01:/root;"),
                verbose=True)

        if pattern:
            cmd = ("docker run --rm --net=host  "
                   "-e TEMPEST_CONF={0} "
                   "-e SKIP_LIST=mcp_skip.list "
                   "-e SOURCE_FILE=keystonercv3  "
                   "-e CUSTOM='--pattern {1} --concurrency 2' "
                   "-v /root/:/home/rally  "
                   "-v /var/log/:/home/rally/rally_reports/ "
                   "-v /etc/ssl/certs/:/etc/ssl/certs/ {2} >> image.output"
                   .format(conf_name, pattern, registry))
        else:
            cmd = ("docker run --rm --net=host  "
                   "-e TEMPEST_CONF={0} "
                   "-e SKIP_LIST=mcp_skip.list "
                   "-e SET=full "
                   "-e CONCURRENCY=2 "
                   "-e SOURCE_FILE=keystonercv3  "
                   "-v /root/:/home/rally "
                   "-v /var/log/:/home/rally/rally_reports/ "
                   "-v /etc/ssl/certs/:/etc/ssl/certs/ {2} >> image.output"
                   .format(conf_name, pattern, registry))
        LOG.info("Running tempest testing on node {0} using the following "
                 "command:\n{1}".format(target_name[0], cmd))

        with self.__underlay.remote(node_name=target_name[0]) as node_remote:
            result = node_remote.execute(cmd, verbose=True)
            LOG.debug("Test execution result is {}".format(result))
        return result

    def download_tempest_report(self, file_fromat='xml', stored_node='gtw01'):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if stored_node in node_name]
        with self.__underlay.remote(node_name=target_node_name[0]) as r:
            result = r.execute('find /var/log/ -name "report_*.{}"'.format(
                file_fromat))
            LOG.debug("Find result {0}".format(result))
            assert len(result['stdout']) > 0, ('No report found, please check'
                                               ' if test run was successful.')
            file_name = result['stdout'][0].rstrip()
            LOG.debug("Found files {0}".format(file_name))
            r.download(destination=file_name, target=os.getcwd())

    def get_node_name_by_subname(self, node_sub_name):
        return [node_name for node_name
                in self.__underlay.node_names()
                if node_sub_name in node_name]

    def warm_shutdown_openstack_nodes(self, node_sub_name, timeout=10 * 60):
        """Gracefully shutting down the node  """
        node_names = self.get_node_name_by_subname(node_sub_name)
        LOG.info('Shutting down nodes {}'.format(node_names))
        for node in node_names:
            LOG.debug('Shutdown node {0}'.format(node))
            self.__underlay.check_call(cmd="shutdown +1", node_name=node)
        for node in node_names:
            LOG.info('Destroy node {}'.format(node))
            self.__hardware.destroy_node(node)
            self.__hardware.wait_for_node_state(
                node, state='offline', timeout=timeout)

    def warm_start_nodes(self, node_sub_name, timeout=10 * 60):
        node_names = self.get_node_name_by_subname(node_sub_name)
        LOG.info('Starting nodes {}'.format(node_names))
        for node in node_names:
            self.__hardware.start_node(node)
            self.__hardware.wait_for_node_state(
                node, state='active', timeout=timeout)

    def warm_restart_nodes(self, node_names, timeout=10 * 60):
        LOG.info('Reboot (warm restart) nodes {0}'.format(node_names))
        self.warm_shutdown_openstack_nodes(node_names, timeout=timeout)
        self.warm_start_nodes(node_names)

    def auth_in_horizon(self, host, port, user, password):
        client = requests.session()
        url = "http://{0}:{1}".format(
            self.__config.openstack.horizon_host,
            self.__config.openstack.horizon_port)
        # Retrieve the CSRF token first
        client.get(url, verify=False)  # sets cookie
        if not len(client.cookies):
            login_data = dict(
                username=self.__config.openstack.horizon_user,
                password=self.__config.openstack.horizon_password,
                next='/')
            resp = client.post(url, data=login_data,
                               headers=dict(Referer=url), verify=False)
            LOG.debug("Horizon resp {}".format(resp))
            assert 200 == resp.status_code, ("Failed to auth in "
                                             "horizon. Response "
                                             "{0}".format(resp.status_code))
        else:
            login_data = dict(
                username=self.__config.openstack.horizon_user,
                password=self.__config.openstack.horizon_password,
                next='/')
            csrftoken = client.cookies.get('csrftoken', None)
            if csrftoken:
                login_data['csrfmiddlewaretoken'] = csrftoken

            resp = client.post(url, data=login_data,
                               headers=dict(Referer=url), verify=False)
            LOG.debug("Horizon resp {}".format(resp))
            assert 200 == resp.status_code, ("Failed to auth in "
                                             "horizon. Response "
                                             "{0}".format(resp.status_code))
