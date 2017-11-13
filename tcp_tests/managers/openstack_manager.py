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

    def run_tempest(
            self,
            target='gtw01', pattern=None,
            conf_name='lvm_mcp.conf',
            registry=None):
        if not registry:
            registry = ('{}/mirantis'
                        '/oscore/rally-tempest'
                        ':latest'.format(settings.DOCKER_REGISTRY))
        target_name = [node_name for node_name
                       in self.__underlay.node_names() if target in node_name]

        if pattern:
            cmd = ("docker run --rm --net=host  "
                   "-e TEMPEST_CONF={0} "
                   "-e SKIP_LIST=mcp_skip.list "
                   "-e SOURCE_FILE=keystonercv3  "
                   "-e CUSTOM='--pattern {1}' "
                   "-v /root/:/home/rally {2} "
                   "-v /etc/ssl/certs/:/etc/ssl/certs/ >> image.output"
                   .format(conf_name, pattern, registry))
        else:
            cmd = ("docker run --rm --net=host  "
                   "-e TEMPEST_CONF={0} "
                   "-e SKIP_LIST=mcp_skip.list "
                   "-e SOURCE_FILE=keystonercv3  "
                   "-v /root/:/home/rally {2}"
                   "-v /etc/ssl/certs/:/etc/ssl/certs/ >> image.output"
                   .format(conf_name, pattern, registry))
        LOG.info("Restart keepalived service before running tempest tests")
        restart_keepalived_cmd = ("salt --hard-crash "
                                  "--state-output=mixed "
                                  "--state-verbose=True "
                                  "-C 'I@keepalived:cluster:enabled:True' "
                                  "service.restart keepalived")
        self.__underlay.check_call(cmd=restart_keepalived_cmd,
                                   host=self.__config.salt.salt_master_host)
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
            result = r.execute('find /root -name "report_*.{}"'.format(
                file_fromat))
            LOG.debug("Find result {0}".format(result))
            assert len(result['stdout']) > 0, ('No report find, please check'
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
