#    Copyright 2019 Mirantis, Inc.
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
import json
import pytest

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class TestUbuntuSecurityUpdates(object):
    """Test class for verification of obtaining Ubuntu security updates"""

    ENV_NAME = settings.ENV_NAME
    UPGRADE_CMD = (
        'export DEBIAN_FRONTEND=noninteractive && '
        'apt-get update && '
        'apt-get -y upgrade && '
        'apt-get -y -o Dpkg::Options::="--force-confdef" '
        '           -o Dpkg::Options::="--force-confnew" dist-upgrade'
    )
    INST_LINUX_HEADERS_CMD = (
        "export DEBIAN_FRONTEND=noninteractive && "
        "apt-get -y install linux-headers-generic"
    )

    UPDATE_JOB_NAME = "deploy-update-package"
    UPDATE_JOB_PARAMETERS = {
        "ASK_CONFIRMATION": False,
        "TARGET_SERVERS": ''
    }

    SANITY_JOB_NAME = 'cvp-sanity'
    SANITY_JOB_PARAMETERS = {
        'EXTRA_PARAMS': {
            'envs': ["tests_set=-k 'not test_ceph_health'"]
        }
    }

    JENKINS_START_TIMEOUT = 60

    def get_available_pkg_updates(self, nodes, salt):
        """Collect available package updates for given nodes

        :param nodes: list, nodes to collect available updates for
        :param salt: SaltManager, tcp-qa Salt manager instance
        :return: dict, update candidates for nodes
        """
        updates = {}
        for node in nodes:
            updates[node] = salt.local(
                node, "pkg.list_upgrades")['return'][0][node]
        return updates

    def run_cvp_sanity(self, dt):
        """A wrapper for executing cvp-sanity pipeline

        :param dt: DrivetrainManager, tcp-qa Drivetrain manager instance
        :return: str, build execution status of cvp-sanity pipeline
        """
        return dt.start_job_on_cid_jenkins(
            job_name=self.SANITY_JOB_NAME,
            job_parameters=self.SANITY_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=60 * 15
        )

    def reboot_hw_node(self, ssh, salt, node):
        """Reboot the given node and wait for it to start back

        :param ssh: UnderlaySSHManager, tcp-qa SSH manager instance
        :param salt: SaltManager, tcp-qa Salt manager instance
        :param node: str, name of the node to reboot
        """
        LOG.info("Sending reboot command to '{}' node.".format(node))
        remote = ssh.remote(node_name=node)
        remote.execute_async("/sbin/shutdown -r now")

        # Wait for restarted node to boot and become accessible
        helpers.wait_pass(
            lambda: salt.local(node, "test.ping", timeout=5),
            timeout=60 * 10, interval=5)

    # TODO: finish the test once ASK_CONFIRMATION option is added to
    # 'deploy-update-package' pipeline
    @pytest.mark.grab_versions
    @pytest.mark.ubuntu_security_updates_pipeline
    def _test_obtaining_ubuntu_security_updates_via_pipeline(
            self, salt_actions, drivetrain_actions, show_step):
        """Test obtaining Ubuntu security updates using Jenkins

        Scenario:
            1. Collect available package upgrades for nodes of the given server
               role
            2. Execute deploy-update-package pipeline for the given server role
            3. Collect available package upgrades for server role nodes again
            4. Check that there is no candidates for upgrade
            5. Run cvp-sanity tests

        Duration: ~  min
        """
        salt = salt_actions
        dt = drivetrain_actions

        role = "mon*"
        nodes = salt.local(role, "test.ping")['return'][0].keys()

        # Collect available package upgrades for nodes
        show_step(1)
        updates = self.get_available_pkg_updates(nodes, salt)
        LOG.info("Packages to be updated on nodes:\n{}".format(
                json.dumps(updates, indent=4)))

        # Execute 'deploy-update-package' pipeline to upgrade packages on nodes
        show_step(2)
        self.UPDATE_JOB_PARAMETERS["TARGET_SERVERS"] = role
        status = dt.start_job_on_cid_jenkins(
            job_name=self.UPDATE_JOB_NAME,
            job_parameters=self.UPDATE_JOB_PARAMETERS,
            start_timeout=self.JENKINS_START_TIMEOUT,
            build_timeout=60 * 15
        )
        assert status == 'SUCCESS', (
            "'{}' job run status is {} after upgrading packages on {} nodes. "
            "Please check the build and executed stages.".format(
                self.UPDATE_JOB_NAME, status, role)
        )

        # Collect available package upgrades for nodes again
        show_step(3)
        post_upgrade = self.get_available_pkg_updates(nodes, salt)

        # Check that there is no available package upgrades
        show_step(4)
        for node in nodes:
            assert not post_upgrade[node], (
                "{} node still has upgrade candidates. Please check the "
                "following packages and the reason why they are not "
                "updated:\n{}".format(node, post_upgrade[node])
            )

        # Execute cvp-sanity tests
        show_step(5)
        status = self.run_cvp_sanity(dt)
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing CVP-Sanity "
            "tests".format(
                self.SANITY_JOB_NAME, status)
        )

    @pytest.mark.grab_versions
    @pytest.mark.ubuntu_security_updates_manual_infra_vms
    def test_obtaining_ubuntu_security_updates_manual_infra_vms(
            self, salt_actions, drivetrain_actions, show_step):
        """Test obtaining Ubuntu security updates on virtual infra nodes.
        Repeat the scenario for 01, 02 and 03 indexes of nodes.

        Scenario:
            1. Select set of virtual nodes for upgrade
            2. Collect available package upgrades for the nodes
            3. Upgrade the nodes
            4. Collect available package upgrades for the nodes again
            5. Check that there is no candidates for upgrade on the nodes
            6. Run cvp-sanity tests

        Duration: ~ 100 min
        """
        salt = salt_actions
        dt = drivetrain_actions

        for index in ('01', '02', '03'):
            msg = ("# Executing scenario for '{i}' index of nodes #".format(
                i=index))
            LOG.info(
                "\n\n{pad}\n{msg}\n{pad}".format(pad="#" * len(msg), msg=msg))

            # Select set of nodes for current iteration of updates
            show_step(1)
            tgt = "*{}* and E@^(?!kvm|cfg|cmp|osd).*$".format(index)
            nodes = salt.local(tgt, "test.ping")['return'][0].keys()
            LOG.info("Nodes to be upgraded:\n{}".format(
                json.dumps(nodes, indent=4)))

            # Collect available package upgrades for the nodes
            show_step(2)
            updates = self.get_available_pkg_updates(nodes, salt)

            # Upgrade the selected nodes
            show_step(3)
            for node in nodes:
                LOG.info(
                    "Starting upgrade of '{}' node.\nThe following packages "
                    "will be updated:\n{}".format(
                        node, json.dumps(updates[node], indent=4))
                )
                salt.cmd_run(node, self.UPGRADE_CMD)

            # Collect available package upgrades for the nodes again
            show_step(4)
            post_upgrade = self.get_available_pkg_updates(nodes, salt)

            # Check that there is no package upgrades candidates on the nodes
            show_step(5)
            missed_upd = {
                node: pkgs for (node, pkgs) in post_upgrade.items() if pkgs}
            assert not missed_upd, (
                "{} nodes still have upgrade candidates. Please check the "
                "nodes and reason why the listed packages are not "
                "updated:\n{}".format(
                    missed_upd.keys(), json.dumps(missed_upd, indent=4))
            )

        # Execute cvp-sanity tests
        show_step(6)
        status = self.run_cvp_sanity(dt)
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing CVP-Sanity smoke "
            "tests".format(self.SANITY_JOB_NAME, status))

    @pytest.mark.grab_versions
    @pytest.mark.ubuntu_security_updates_manual_hw_nodes
    def test_obtaining_ubuntu_security_updates_manual_hw_nodes(
            self,
            salt_actions,
            underlay_actions,
            drivetrain_actions,
            show_step):
        """Test obtaining Ubuntu security updates on HW nodes.
        Repeat the scenario for 01, 02 and 03 indexes of nodes.

        Scenario:
            1. Select set HW nodes for upgrade
            2. Collect available package upgrades for the nodes
            3. Upgrade the nodes
            4. Collect available package upgrades for the nodes again
            5. Check that there is no candidates for upgrade on the nodes
            6. Run cvp-sanity tests

        Duration: ~ 70 min
        """
        salt = salt_actions
        ssh = underlay_actions
        dt = drivetrain_actions

        for index in ('01', '02', '03'):
            msg = ("# Executing scenario for '{i}' index of nodes #".format(
                i=index))
            LOG.info(
                "\n\n{pad}\n{msg}\n{pad}".format(pad="#" * len(msg), msg=msg))

            # Select set of nodes for current iteration of updates
            show_step(1)
            tgt = "E@^(kvm|cmp).?{}.*$".format(index)
            nodes = salt.local(tgt, "test.ping")['return'][0].keys()
            LOG.info("Nodes to be upgraded:\n{}".format(
                json.dumps(nodes, indent=4)))

            # Collect available package upgrades for the nodes
            show_step(2)
            updates = self.get_available_pkg_updates(nodes, salt)

            # Upgrade the selected nodes
            show_step(3)
            for node in nodes:
                LOG.info(
                    "Starting upgrade of '{}' node.\nThe following packages "
                    "will be updated:\n{}".format(
                        node, json.dumps(updates[node], indent=4))
                )
                salt.cmd_run(node, self.UPGRADE_CMD)
                # Update Linux headers on compute nodes
                if "cmp" in node:
                    LOG.info(
                        "Updating linux headers on '{}' node.".format(node))
                    salt.cmd_run(node, self.INST_LINUX_HEADERS_CMD)

                # Reboot the node after upgrade
                LOG.info("Starting reboot of '{}' node.".format(node))
                self.reboot_hw_node(ssh, salt, node)
                LOG.info("'{}' node is back after reboot.".format(node))

            # Collect available package upgrades for the nodes again
            show_step(4)
            post_upgrade = self.get_available_pkg_updates(nodes, salt)

            # Check that there is no package upgrades candidates on the nodes
            show_step(5)
            missed_upd = {
                node: pkgs for (node, pkgs) in post_upgrade.items() if pkgs}
            assert not missed_upd, (
                "{} nodes still have upgrade candidates. Please check the "
                "nodes and reason why the listed packages are not "
                "updated:\n{}".format(
                    missed_upd.keys(), json.dumps(missed_upd, indent=4))
            )

        # Execute cvp-sanity tests
        show_step(6)
        status = self.run_cvp_sanity(dt)
        assert status == 'SUCCESS', (
            "'{0}' job run status is {1} after executing CVP-Sanity "
            "tests".format(self.SANITY_JOB_NAME, status))
