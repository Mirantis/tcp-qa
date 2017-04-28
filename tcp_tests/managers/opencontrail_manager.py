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

from tcp_tests.managers.execute_commands import ExecuteCommandsMixin


class OpenContrailManager(ExecuteCommandsMixin):
    """docstring for OpenstackManager"""

    __config = None
    __underlay = None
    _openstack_actions = None

    def __init__(self, config, underlay, openstack_deployed):
        self.__config = config
        self.__underlay = underlay
        self._openstack_actions = openstack_deployed
        super(OpenContrailManager, self).__init__(
            config=config, underlay=underlay)

    def prepare_tests(self, commands):
        self.execute_commands(commands=commands,
                              label="Prepare Juniper contrail-test")

    def run_tests(self, tags='', features=''):
        cmd = "salt 'ctl01*' grains.get fqdn|tail -n1"
        result = self.__underlay.check_call(
            cmd, host=self.__config.salt.salt_master_host)

        ctl01_name = result['stdout'].strip()

        cmd = '. /etc/contrail/openstackrc; ' \
              'cd /opt/contrail-test; ./run_tests.sh'
        if tags != '':
            cmd += ' --tags ' + tags

        if features != '':
            cmd += ' --features ' + features

        self.__underlay.check_call(
            cmd,
            node_name=ctl01_name)
