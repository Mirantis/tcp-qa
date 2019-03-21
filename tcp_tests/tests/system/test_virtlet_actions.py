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
import os

from tcp_tests.managers.k8s import read_yaml_file
from tcp_tests import logger

LOG = logger.logger


class TestVirtletActions(object):
    """Test class for testing Virtlet actions"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.k8s_virtlet
    @pytest.mark.k8s_system
    def test_virtlet_create_delete_vm(self, show_step, config, k8s_deployed):
        """Test for deploying an mcp environment with virtlet

        Scenario:
            1. Start VM as a virtlet pod
            2. Wait active state of VM
            3. Delete VM and wait to delete pod

        """

        if not config.k8s_deploy.kubernetes_virtlet_enabled:
            pytest.skip("Test requires Virtlet addon enabled")
        data_dir = os.path.join(os.path.dirname(__file__), 'testdata/k8s')

        show_step(1)
        vm_pod = k8s_deployed.api.pods.create(
            body=read_yaml_file(data_dir, 'cirros-vm.yaml'))

        show_step(2)
        vm_pod.wait_running(timeout=600)

        show_step(3)
        vm_pod.delete()

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.k8s_virtlet
    @pytest.mark.k8s_system
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
        data_dir = os.path.join(os.path.dirname(__file__), 'testdata/k8s')
        cpu = 2
        memory_mb = 512

        show_step(1)
        pod_body = read_yaml_file(data_dir, 'cirros-vm.yaml')
        pod_body['metadata']['annotations']['VirtletVCPUCount'] = str(cpu)
        pod_body['spec']['containers'][0]['resources']['limits']['memory'] = \
            '{}Mi'.format(memory_mb)

        show_step(2)
        vm_pod = k8s_deployed.api.pods.create(body=pod_body)
        vm_pod.wait_running(timeout=600)

        show_step(3)
        stats = k8s_deployed.virtlet.virsh_domstats(vm_pod)
        assert int(stats['vcpu.current']) == cpu
        assert int(stats['balloon.maximum'])/1024 == memory_mb

        show_step(4)
        vm_pod.delete()

    @pytest.mark.prepare_log(filepath='/tmp/virtlet-conformance/'
                                      'virtlet_conformance.log')
    @pytest.mark.merge_xunit(path='/tmp/virtlet-conformance',
                             output='/root/report.xml')
    @pytest.mark.download(name=['virtlet_conformance.log',
                                'report.xml'])
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_virtlet_conformance(self, show_step, config, k8s_deployed,
                                 conformance_helper):
        """Test run of virtlet conformance tests

        Scenario:
            1. Perform virtlet conformance

        """

        show_step(1)
        k8s_deployed.start_conformance_inside_pod(cnf_type='virtlet')
