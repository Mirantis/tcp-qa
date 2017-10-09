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


class OSServiceCheckers(object):
    """docstring for OSServiceCheckers"""

    def assert_res(self, r):
        ret = r[0]
        assert ret.get('return')
        assert len(ret.get('return')[0]) == 3
        hosts = ret.get('return')[0]
        assert all(['PASS' in one[1] for one in hosts.items()])

    def cmd_has(self, pattern, f):
        cmd_has = '''(grep -q '{pattern}' {f}) && echo PASS || echo FAIL'''
        cmd = cmd_has.format(pattern=pattern, f=f)
        LOG.debug(cmd)
        return cmd

    def cmd_hasnt(self, pattern, f):
        cmd_hasnt = \
            '''(! grep -q '{pattern}' {f}) && echo PASS || echo FAIL'''
        cmd = cmd_hasnt.format(pattern=pattern, f=f)
        LOG.debug(cmd)
        return cmd

    def check_nova(self, salt):
        cmd = self.cmd_has(
            pattern='"context_is_admin":', f='/etc/nova/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@nova:controller', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_has(
            pattern='"compute:create":', f='/etc/nova/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@nova:controller', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_hasnt(
            pattern='"compute:create:attach_network":',
            f='/etc/nova/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@nova:controller', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

    def check_cinder(self, salt):
        cmd = self.cmd_has(
            pattern='"volume:delete":', f='/etc/cinder/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@cinder:controller', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_hasnt(
            pattern='"volume:extend":', f="/etc/cinder/policy.json")
        LOG.info(cmd)
        ret = salt.run_state('I@cinder:controller', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

    def check_heat(self, salt):
        cmd = self.cmd_has(
            pattern='"context_is_admin":', f='/etc/heat/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@heat:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_has(
            pattern='"deny_stack_user":', f='/etc/heat/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@heat:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_has(
            pattern='"deny_everybody":', f='/etc/heat/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@heat:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_has(
            pattern='"cloudformation:ValidateTemplate":',
            f='/etc/heat/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@heat:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_hasnt(
            pattern='"cloudformation:DescribeStackResources":',
            f='/etc/heat/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@heat:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

    def check_glance(self, salt):
        cmd = self.cmd_has(
            pattern='"publicize_image":', f='/etc/glance/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@glance:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_hasnt(
            pattern='"add_member":', f='/etc/glance/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@glance:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

    def check_neutron(self, salt):
        cmd = self.cmd_has(
            pattern='"create_subnet":', f='/etc/neutron/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@neutron:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_has(
            pattern='"get_network:queue_id":', f='/etc/neutron/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@neutron:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_hasnt(
            pattern='"create_network:shared":', f='/etc/neutron/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@neutron:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

    def check_ceilometer(self, salt):
        cmd = self.cmd_has(
            pattern='"segregation"', f='/etc/ceilometer/policy.json')
        LOG.info(cmd)
        ret = salt.run_state('I@ceilometer:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

        cmd = self.cmd_hasnt(
            pattern='"telemetry:get_resource"',
            f='/etc/ceilometer/policy.json')
        ret = salt.run_state('I@ceilometer:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)

    def check_keystone(self, salt):
        cmd = self.cmd_has(
            pattern='"admin_or_token_subject":', f='/etc/keystone/policy.json')

        LOG.info(cmd)
        ret = salt.run_state('I@keystone:server', 'cmd.run', cmd)
        LOG.info(ret)
        self.assert_res(ret)


class TestOSAIOServicesPolicy(OSServiceCheckers):
    """Test class for testing OpenStack services policy"""

    def test_services_with_custom_policy_json(
            self, underlay, openstack_deployed, salt_actions, show_step):
        """Test add policy for Nova service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Verify nova policy.json
            5. Verify cinder policy.json
            6. Verify heat policy.json
            7. Verify glance policy.json
            8. Verify neutron policy.json
            9. Verify keystone policy.json
            10. Verify ceilometer policy.json. Skipped due absence of ceilometer  # noqa

        """
        salt = salt_actions
        # STEP #1,2,3
        show_step(1)
        show_step(2)
        show_step(3)

        # STEP #4
        show_step(4)
        self.check_nova(salt)

        # STEP #5
        show_step(5)
        self.check_cinder(salt)

        # STEP #6
        show_step(6)
        self.check_heat(salt)

        # STEP #7
        show_step(7)
        self.check_glance(salt)

        # STEP #8
        show_step(8)
        self.check_neutron(salt)

        # STEP #9
        show_step(9)
        self.check_keystone(salt)

        # STEP #10
        # FIXME: Enable when template has a ceilometer
        # show_step(10)
        # self.check_ceilometer(salt)

        #
        LOG.info("*************** DONE **************")


class TestOSServicesPolicy(OSServiceCheckers):
    """Test class for testing OpenStack services policy"""

    # https://github.com/salt-formulas/salt-formula-nova/pull/17 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_policy_for_nova(self, underlay, openstack_deployed, salt_actions,
                             show_step):
        """Test add policy for Nova service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        self.check_nova(salt)
        LOG.info("*************** DONE **************")

    # https://github.com/salt-formulas/salt-formula-cinder/pull/13 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_policy_for_cinder(self, underlay, openstack_deployed,
                               salt_actions, show_step):
        """Test add policy for Cinder service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Add policy for service
            5. Regenerate by salt
            6. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        show_step(6)
        self.check_cinder(salt)
        LOG.info("*************** DONE **************")

    # https://github.com/salt-formulas/salt-formula-heat/pull/5 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_policy_for_heat(self, underlay, openstack_deployed, salt_actions,
                             show_step):
        """Test add policy for Cinder service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Add policy for service
            5. Regenerate by salt
            6. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        show_step(6)
        self.check_heat(salt)
        LOG.info("*************** DONE **************")

    # https://github.com/salt-formulas/salt-formula-glance/pull/9 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_policy_for_glance(self, underlay, openstack_deployed,
                               salt_actions, show_step):
        """Test add policy for Cinder service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Add policy for service
            5. Regenerate by salt
            6. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        show_step(6)
        self.check_cinder(salt)
        LOG.info("*************** DONE **************")

    # https://github.com/salt-formulas/salt-formula-ceilometer/pull/2 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.skip(reason="Skipped due no have ceilometer in environment")
    def test_policy_for_ceilometer(self, underlay, openstack_deployed,
                                   salt_actions, show_step):
        """Test add policy for Cinder service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Add policy for service
            5. Regenerate by salt
            6. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        show_step(6)
        self.check_ceilometer(salt)
        LOG.info("*************** DONE **************")

    # https://github.com/salt-formulas/salt-formula-neutron/pull/8 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_policy_for_neutron(self, underlay, openstack_deployed,
                                salt_actions, show_step):
        """Test add policy for Cinder service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Add policy for service
            5. Regenerate by salt
            6. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        show_step(6)
        self.check_neutron(salt)
        LOG.info("*************** DONE **************")

    # https://github.com/salt-formulas/salt-formula-keystone/pull/11 - Merged
    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    def test_policy_for_keystone(self, underlay, openstack_deployed,
                                 salt_actions, show_step):
        """Test add policy for Cinder service

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Add policy for service
            5. Regenerate by salt
            6. Verify

        """
        salt = salt_actions
        show_step(1)
        show_step(2)
        show_step(3)
        show_step(4)
        show_step(5)
        show_step(6)
        self.check_keystone(salt)
        LOG.info("*************** DONE **************")
