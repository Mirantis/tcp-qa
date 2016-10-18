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

import yaml

from devops.helpers import helpers

from tcp_tests.helpers import exceptions
from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class TCPManager(object):
    """docstring for TCPManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        self._api_client = None

        if self.__config.tcp.tcp_host == '0.0.0.0':
            # Temporary workaround. Underlay should be extended with roles
            tcp_nodes = self.__underlay.node_names()
            self.__config.tcp.tcp_host = \
                self.__underlay.host_by_node_name(tcp_nodes[0])

        super(TCPManager, self).__init__()

    def show_tcp_config(self):
        cmd = 'reclass -n {0}'.format(self.__underlay.node_names()[0])
        self.__underlay.sudo_check_call(cmd, host=self.__config.tcp.tcp_host)

    def install_tcp(self):
        raise Exception("Not implemented!")
