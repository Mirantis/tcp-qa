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
            if ext.UNDERLAY_NODE_ROLES.k8s_virtlet in i['roles']]
        super(VirtletManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install Virtlet project')
        self.__config.virtlet.virtlet_installed = True

    def run_vm(self, name=None, yaml_path='virtlet/examples/cirros-vm.yaml'):
        if not name:
            name = 'virtlet-vm-{}'.format(uuid4())
        virt_node = self.virtlet_nodes[0]
        cmd = (
            "kubectl convert -f {0} --local "
            "-o json | jq '.metadata.name|=\"{1}\"' | kubectl create -f -")
        self.__underlay.check_call(
            cmd.format(name, yaml_path),
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

    def adjust_cirros_resources(
            self, cpu=2, memory='256',
            target_yaml='virtlet/examples/cirros-vm-exp.yaml'):
        virt_node = self.virtlet_nodes[0]
        # We will need to change params in case of example change
        cmd = ("cd ~/virtlet/examples && "
               "cp cirros-vm.yaml {2} && "
               "sed -r 's/^(\s*)(VirtletVCPUCount\s*:\s*\"1\"\s*$)/ "
               "\1VirtletVCPUCount: \"{0}\"/' {2} && "
               "sed -r 's/^(\s*)(memory\s*:\s*128Mi\s*$)/\1memory: "
               "{1}Mi/' {2}".format(cpu, memory, target_yaml))
        self.__underlay.check_call(cmd, node_name=virt_node['node_name'])

    def get_domain_name(self, vm_name):
        virt_node = self.virtlet_nodes[0]
        cmd = ("~/virtlet/examples/virsh.sh list | grep -i {0} "
               "| awk {{'print $2'}}".format(vm_name))
        result = self.__underlay.check_call(cmd,
                                            node_name=virt_node['node_name'])
        return result['stdout'].strip()

    def get_vm_cpu_count(self, domain_name):
        virt_node = self.virtlet_nodes[0]
        cmd = ("~/virtlet/examples/virsh.sh dumpxml {0} | "
               "grep 'cpu' | grep -o '[[:digit:]]*'".format(domain_name))
        result = self.__underlay.check_call(cmd,
                                            node_name=virt_node['node_name'])
        return int(result['stdout'].strip())

    def get_vm_memory_count(self, domain_name):
        virt_node = self.virtlet_nodes[0]
        cmd = ("~/virtlet/examples/virsh.sh dumpxml {0} | "
               "grep 'memory unit' | "
               "grep -o '[[:digit:]]*'".format(domain_name))
        result = self.__underlay.check_call(cmd,
                                            node_name=virt_node['node_name'])
        return int(result['stdout'].strip())

    def get_domain_id(self, domain_name):
        virt_node = self.virtlet_nodes[0]
        cmd = ("virsh dumpxml {} | grep id=\' | "
               "grep -o [[:digit:]]*".format(domain_name))
        result = self.__underlay.check_call(cmd,
                                            node_name=virt_node['node_name'])
        return int(result['stdout'].strip())

    def list_vm_volumes(self, domain_name):
        virt_node = self.virtlet_nodes[0]
        domain_id = self.get_domain_id(domain_name)
        cmd = ("~/virtlet/examples/virsh.sh domblklist {} | "
               "tail -n +3 | awk {{'print $2'}}".format(domain_id))
        result = self.__underlay.check_call(cmd,
                                            node_name=virt_node['node_name'])
        return result['stdout'].strip()
