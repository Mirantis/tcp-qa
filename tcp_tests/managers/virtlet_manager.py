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

from tcp_tests.helpers import ext
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin

from devops.helpers import helpers


class VirtletManager(ExecuteCommandsMixin):
    """docstring for VirtletManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        self.virtlet_nodes = [
            i for i in self.__config.underlay.ssh
            if ext.UNDERLAY_NODE_ROLES.virtlet_node in i['roles']]
        super(VirtletManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install Virtlet project')
        self.__config.virtlet.virtlet_installed = True

    def run_vm(self, name=None):
        if not name:
            name = 'virtlet-vm-{}'.format(uuid4())
        virt_node = self.virtlet_nodes[0]
        cmd = (
            "kubectl convert -f virtlet/examples/cirros-vm.yaml --local "
            "-o json | jq '.metadata.name|=\"{}\"' | kubectl create -f -")
        self.__underlay.check_call(
            cmd.format(name),
            node_name=virt_node['node_name'])
        return name

    def get_vm_info(self, name, jsonpath="{.status.phase}", expected=None):
        virt_node = self.virtlet_nodes[0]
        cmd = "kubectl get po {} -n default".format(name)
        if jsonpath:
            cmd += " -o jsonpath={}".format(jsonpath)
        return self.__underlay.check_call(
            cmd, node_name=virt_node['node_name'], expected=expected)

    def wait_active_state(self, name, timeout=180):
        helpers.wait(
            lambda: self.get_vm_info(name)['stdout'][0] == 'Running',
            timeout=timeout,
            timeout_msg="VM {} didn't Running state in {} sec. "
                        "Current state: ".format(
                name, timeout, self.get_vm_info(name)['stdout'][0]))

    def delete_vm(self, name, timeout=180):
        virt_node = self.virtlet_nodes[0]
        cmd = "kubectl delete po -n default {}".format(name)
        self.__underlay.check_call(cmd, node_name=virt_node['node_name'])

        helpers.wait(
            lambda:
            "Error from server (NotFound):" in
            " ".join(self.get_vm_info(name, expected=[0, 1])['stderr']),
            timeout=timeout,
            timeout_msg="VM {} didn't Running state in {} sec. "
                        "Current state: ".format(
                name, timeout, self.get_vm_info(name)['stdout'][0]))
