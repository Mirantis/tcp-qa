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

from tcp_tests.managers.execute_commands import ExecuteCommandsMixin


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
        # Get any controller
        cmd = "salt 'ctl01*' grains.get fqdn|tail -n1"
        result = self.__underlay.check_call(
            cmd, host=self.__config.salt.salt_master_host)

        ctl01_name = result['stdout'].strip()

        # Get virtlet node hostname
        cmd = "kubectl get po -n kube-system -o=wide | grep virtlet | " \
              "awk {'print $7'}"
        result = self.__underlay.check_call(cmd, node_name=ctl01_name)
        return result['stdout'].strip()

    def adjust_cirros_resources(self, cpu=2, memory='256Mi'):
        virtlet_node = self.get_virtlet_node()
        # We will need to change params in case of example change
        cmd = "cd ~/virtlet/examples && " \
              "cp cirros-vm.yaml cirros-vm-exp.yaml && " \
              "sed -r 's/^(\s*)(VirtletVCPUCount\s*:\s*\"1\"\s*$)/" \
              "\1VirtletVCPUCount: \"{0}\"/' cirros-vm-exp.yaml && " \
              "sed -r 's/^(\s*)(memory\s*:\s*128Mi\s*$)/\1memory: " \
              "{1}/' cirros-vm-exp.yaml".format(cpu, memory)
        self.__underlay.check_call(cmd, node_name=virtlet_node)

    def get_domain_name(self):
        pass

    def get_vm_cpu_count(self, domain_id):
        pass

    def get_vm_memory_count(self, domain_id):
        pass

    def start_vm(self):
        pass

    def delete_vm(self):
        pass
