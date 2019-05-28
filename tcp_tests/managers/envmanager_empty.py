#    Copyright 2016 Mirantis, Inc.
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

from tcp_tests import settings
from tcp_tests import settings_oslo


class EnvironmentManagerEmpty(object):
    """Class-helper for creating VMs via devops environments"""

    __config = None

    def __init__(self, config=None):
        """Initializing class instance and create the environment

        :param config: oslo.config object
        :param config.hardware.conf_path: path to devops YAML template
        :param config.hardware.current_snapshot: name of the snapshot that
                                                 descriebe environment status.
        """
        self.__config = config

    def get_ssh_data(self, roles=None):
        raise Exception("EnvironmentManagerEmpty doesn't have SSH details. "
                        "Please provide SSH details in config.underlay.ssh")

    def create_snapshot(self, name, **kwargs):
        """Store environmetn state into the config object

        - Store the state of the environment <name> to the 'config' object
        - Save 'config' object to a file 'config_<name>.ini'
        """
        if not settings.MAKE_SNAPSHOT_STAGES:
            msg = ("[ SKIP snapshot '{0}' because MAKE_SNAPSHOT_STAGES=false ]"
                   " {1}".format(name, description or ''))
            LOG.info("\n\n{0}\n{1}".format(msg, '*' * len(msg)))
            return

        self.__config.hardware.current_snapshot = name
        settings_oslo.save_config(self.__config, name)

    def revert_snapshot(self, name):
        """Check the current state <name> of the environment

        - Check that the <name> matches the current state of the environment
          that is stored in the 'self.__config.hardware.current_snapshot'
        - Try to reload 'config' object from a file 'config_<name>.ini'
          If the file not found, then pass with defaults.
        - Set <name> as the current state of the environment after reload

        :param name: string
        """
        if self.__config.hardware.current_snapshot != name:
            raise Exception(
                "EnvironmentManagerEmpty cannot revert nodes from {} to {}"
                .format(self.__config.hardware.current_snapshot, name))

    def start(self):
        """Start environment"""
        pass

    def resume(self):
        """Resume environment"""
        pass

    def suspend(self):
        """Suspend environment"""
        pass

    def stop(self):
        """Stop environment"""
        pass

    def has_snapshot(self, name):
        return self.__config.hardware.current_snapshot == name

    def has_snapshot_config(self, name):
        return self.__config.hardware.current_snapshot == name

    def delete_environment(self):
        """Delete environment"""
        pass

    def warm_shutdown_nodes(self, underlay, nodes_prefix, timeout=600):
        raise Exception(
            "Node shutdown method unsupported on this environment manager")

    def warm_restart_nodes(self, underlay, nodes_prefix, timeout=600):
        raise Exception(
            "Node restart method unsupported on this environment manager")
