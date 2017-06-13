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
import copy
import time

import pytest

from tcp_tests import settings
from tcp_tests.helpers import ext
from tcp_tests import logger

LOG = logger.logger


@pytest.mark.deploy
class TestVirtletInstall(object):
    """Test class for testing Virtlet deploy"""

    #salt_cmd = 'salt -l debug '  # For debug output
    #salt_call_cmd = 'salt-call -l debug '  # For debug output
    salt_cmd = 'salt --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    salt_call_cmd = 'salt-call --hard-crash --state-output=mixed --state-verbose=False '  # For cause only output
    #salt_cmd = 'salt --state-output=terse --state-verbose=False '  # For reduced output
    #salt_call_cmd = 'salt-call --state-output=terse --state-verbose=False '  # For reduced output

    # @pytest.mark.snapshot_needed
    # @pytest.mark.fail_snapshot
    def test_virtlet_install(self, underlay, virtlet_deployed,
                                     show_step):
        """Test for deploying an mcp environment with virtlet

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup virtlet

        """
        LOG.info("*************** DONE **************")

    def test_virtlet_install_with_ceph(self, underlay, virtlet_ceph_deployed,
                                       show_step):
        """Test for deploying an mcp environment with virtlet and one-node
        Ceph cluster.

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup virtlet
            5. Launch Ceph one-node cluster in docker

        """
        LOG.info("*************** DONE **************")

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
        target_memory_kb = target_memory*1024
        target_yaml = 'cirros-vm-exp.yaml'
        virtlet_actions.adjust_cirros_resources(cpu=target_cpu,
                                                memory=target_memory,
                                                target_yaml=target_yaml)
        virtlet_actions.start_vm(target_yaml)
        virtlet_actions.wait_for_vm_pod_status('Running')
        domain_id = virtlet_actions.get_domain_name()
        cpu = virtlet_actions.get_vm_cpu_count(domain_id)
        mem = virtlet_actions.get_vm_memory_count(domain_id)
        fail_msg = '{0} is not correct memory unit for VM. Correct is {1}'.\
            format(mem, target_memory_kb)
        assert target_memory_kb == mem, fail_msg
        fail_msg = '{0} is not correct cpu cores count for VM. ' \
                   'Correct is {1}'.format(cpu, target_cpu)
        assert target_cpu == cpu, fail_msg
        virtlet_actions.delete_vm(target_yaml)
