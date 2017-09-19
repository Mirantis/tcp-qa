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

from tcp_tests import logger

LOG = logger.logger


class TestVirtletActions(object):
    """Test class for testing Virtlet actions"""

    def test_virtlet_create_delete_vm(self, underlay, virtlet_deployed,
                                      show_step, virtlet_actions):
        """Test for deploying an mcp environment with virtlet

        Scenario:
            1. Start VM as a virtlet pod
            2. Wait active state of VM
            3. Delete VM and wait to delete pod

        """
        vm_name = virtlet_actions.run_vm()
        virtlet_actions.wait_active_state(vm_name)
        virtlet_actions.delete_vm(vm_name)

    def test_vm_resource_quotas(self, underlay, virtlet_deployed, show_step,
                                virtlet_actions):
        """Test for deploying a VM with specific quotas

        Scenario:
            1. Prepare VM's yaml
            2. Start a VM
            3. Check that VM resources is equal to provided in yaml
            4. Destroy VM

        """

        target_cpu = 2  # Cores
        target_memory = 256  # Size in MB
        target_memory_kb = target_memory * 1024
        target_yaml = 'virtlet/examples/cirros-vm-exp.yaml'
        virtlet_actions.adjust_cirros_resources(cpu=target_cpu,
                                                memory=target_memory,
                                                target_yaml=target_yaml)
        vm_name = virtlet_actions.run_vm(target_yaml)
        virtlet_actions.wait_active_state(vm_name)
        domain_name = virtlet_actions.get_domain_name(vm_name)
        cpu = virtlet_actions.get_vm_cpu_count(domain_name)
        mem = virtlet_actions.get_vm_memory_count(domain_name)
        fail_msg = '{0} is not correct memory unit for VM. Correct is {1}'.\
            format(mem, target_memory_kb)
        assert target_memory_kb == mem, fail_msg
        fail_msg = '{0} is not correct cpu cores count for VM. ' \
                   'Correct is {1}'.format(cpu, target_cpu)
        assert target_cpu == cpu, fail_msg
        virtlet_actions.delete_vm(target_yaml)

    def test_rbd_flexvolume_driver(self, underlay, virtlet_ceph_deployed,
                                   show_step, virtlet_actions):
        """Test for deploying a VM with Ceph RBD volume using flexvolumeDriver

        Scenario:
            1. Start VM with prepared yaml from run-ceph.sh scripts
            2. Check that RBD volume is listed in virsh domblklist for VM
            3. Destroy VM

        """
        # From:
        # https://github.com/Mirantis/virtlet/blob/master/tests/e2e/run_ceph.sh
        target_yaml = "virtlet/tests/e2e/cirros-vm-rbd-volume.yaml"
        vm_name = virtlet_actions.run_vm(target_yaml)
        virtlet_actions.wait_active_state(vm_name)
        domain_name = virtlet_actions.get_domain_name(vm_name)
        vm_volumes_list = virtlet_actions.list_vm_volumes(domain_name)
        assert 'rbd' in vm_volumes_list
        virtlet_actions.delete_vm(target_yaml)
