#    Copyright 2017 Mirantis, Inc.
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

from uuid import uuid4

from tcp_tests.managers.execute_commands import ExecuteCommandsMixin

from devops.helpers import helpers


class VirtletManager(ExecuteCommandsMixin):
    """docstring for VirtletManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        super(VirtletManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install Virtlet project')
        self.__config.virtlet.virtlet_installed = True

    def get_virtlet_node(self):
        return next(i for i in self.__config.underlay.ssh
                    if 'ctl02' in i['node_name'])

    def run_vm(self, name=None):
        if not name:
            name = 'virtlet_vm_{}'.format(uuid4())
        node2 = self.get_virtlet_node()
        cmd = (
            "kubectl convert -f virtlet/examples/cirros-vm.yaml --local "
            "-o json | jq '.metadata.name|=\"{name}\"' | kubectl create -f -")
        self.__underlay.check_call(
            cmd.format(name),
            node_name=node2['node_name'])
        return name

    def wait_active_state(self, name, timeout=180):
        node2 = self.get_virtlet_node()
        cmd="kubectl get po -n default {name} -o jsonpath='{.status.phase}'"
        def get_state():
            return self.__underlay.check_call(cmd.format(name),
                                              node_name=node2['node_name'])

        helpers.wait(
            lambda: get_state() == 'Running',
            timeout=timeout,
            timeout_msg="VM {} didn't Running state in {} sec".format(
                name, timeout))
