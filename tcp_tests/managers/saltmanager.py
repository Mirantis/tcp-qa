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

class SaltManager(object):
    """docstring for SaltManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay


        super(SaltManager, self).__init__()

    def install(self, commands):
        if self.__config.salt.salt_master_host == '0.0.0.0':
            # Temporary workaround. Underlay should be extended with roles
            salt_nodes = self.__underlay.node_names()
            self.__config.salt.salt_master_host = \
                self.__underlay.host_by_node_name(salt_nodes[0])

        self.__underlay.execute_commands(commands)
