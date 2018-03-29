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
import pytest

from tcp_tests import logger

LOG = logger.logger


class TestVirtletActions(object):
    """Test class for testing Virtlet actions"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_virtlet_create_delete_vm(self, show_step, config, k8s_deployed):
        """Test for deploying an mcp environment with virtlet

        Scenario:
            1. Start VM as a virtlet pod
            2. Wait active state of VM
            3. Delete VM and wait to delete pod

        """

        if not config.k8s_deploy.kubernetes_virtlet_enabled:
            pytest.skip("Test requires Virtlet addon enabled")

        k8s_deployed.git_clone('https://github.com/Mirantis/virtlet',
                               '~/virtlet')
        k8s_deployed.install_jq()
        show_step(1)
        vm_name = k8s_deployed.run_vm()
        show_step(2)
        k8s_deployed.wait_active_state(vm_name, timeout=360)
        show_step(3)
        k8s_deployed.delete_vm(vm_name)

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_vm_resource_quotas(self, show_step, config, k8s_deployed):
        """Test for deploying a VM with specific quotas

        Scenario:
            1. Prepare VM's yaml
            2. Start a VM
            3. Check that VM resources is equal to provided in yaml
            4. Destroy VM

        """

        if not config.k8s_deploy.kubernetes_virtlet_enabled:
            pytest.skip("Test requires Virtlet addon enabled")

        k8s_deployed.git_clone('https://github.com/Mirantis/virtlet',
                               '~/virtlet')
        k8s_deployed.install_jq()
        show_step(1)
        target_cpu = 2  # Cores
        target_memory = 256  # Size in MB
        target_memory_kb = target_memory * 1024
        target_yaml = 'virtlet/examples/cirros-vm-exp.yaml'
        k8s_deployed.adjust_cirros_resources(cpu=target_cpu,
                                             memory=target_memory,
                                             target_yaml=target_yaml)
        show_step(2)
        vm_name = k8s_deployed.run_vm(target_yaml)
        k8s_deployed.wait_active_state(vm_name, timeout=360)
        show_step(3)
        domain_name = k8s_deployed.get_domain_name(vm_name)
        cpu = k8s_deployed.get_vm_cpu_count(domain_name)
        mem = k8s_deployed.get_vm_memory_count(domain_name)
        fail_msg = '{0} is not correct memory unit for VM. Correct is {1}'.\
            format(mem, target_memory_kb)
        assert target_memory_kb == mem, fail_msg
        fail_msg = '{0} is not correct cpu cores count for VM. ' \
                   'Correct is {1}'.format(cpu, target_cpu)
        assert target_cpu == cpu, fail_msg
        show_step(4)
        k8s_deployed.delete_vm(target_yaml)

    @pytest.mark.grab_versions
    @pytest.mark.grab_k8s_results(name=['virtlet_conformance.log',
                                        'report.xml'])
    @pytest.mark.fail_snapshot
    def test_virtlet_conformance(self, show_step, config, k8s_deployed,
                                 k8s_logs):
        """Test run of virtlet conformance tests

        Scenario:
            1. Perform virtlet conformance

        """

        show_step(1)
        k8s_deployed.run_virtlet_conformance()

    @pytest.mark.skip(reason="No configuration with ceph and k8s")
    def test_rbd_flexvolume_driver(self, show_step, config, k8s_deployed):
        """Test for deploying a VM with Ceph RBD volume using flexvolumeDriver

        Scenario:
            1. Start VM with prepared yaml from run-ceph.sh scripts
            2. Check that RBD volume is listed in virsh domblklist for VM
            3. Destroy VM

        """
        # From:
        # https://github.com/Mirantis/virtlet/blob/master/tests/e2e/run_ceph.sh
        if not config.k8s_deploy.kubernetes_virtlet_enabled:
            pytest.skip("Test requires Virtlet addon enabled")

        k8s_deployed.git_clone('https://github.com/Mirantis/virtlet',
                               '~/virtlet')
        k8s_deployed.install_jq()

        target_yaml = "virtlet/tests/e2e/cirros-vm-rbd-volume.yaml"
        vm_name = k8s_deployed.run_vm(target_yaml)
        k8s_deployed.wait_active_state(vm_name)
        domain_name = k8s_deployed.get_domain_name(vm_name)
        vm_volumes_list = k8s_deployed.list_vm_volumes(domain_name)
        assert 'rbd' in vm_volumes_list
        k8s_deployed.delete_vm(target_yaml)
