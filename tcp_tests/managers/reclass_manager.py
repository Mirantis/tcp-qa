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

from tcp_tests import logger
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin

LOG = logger.logger


class ReclassManager(ExecuteCommandsMixin):
    """docstring for ReclassManager"""

    __config = None
    __underlay = None
    reclass_tools_cmd = ". venv-reclass-tools/bin/activate; reclass-tools "
    tgt = "cfg01"    # place where the reclass-tools installed

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay

        self.ssh = self.__underlay.remote(host=self.tgt)

        super(ReclassManager, self).__init__(config=config, underlay=underlay)

    def is_existed(self, key):
        if key in self.ssh.check_call(
                "{reclass_tools} get-key {key} /srv/salt/reclass/classes"
                .format(
                    reclass_tools=self.reclass_tools_cmd,
                    key=key
                )):
            LOG.warning("({}) key already exists in reclass".format(key))
            return True
        return False

    def add_key(self, key, value, short_path):
        """
        Shows alert if key exists

        :param key: string, parameters which will be added or updated
        :param value: value of key
        :param short_path: path to reclass yaml file.
            It takes into account default path where the reclass locates.
            May look like cluster/*/cicd/control/leader.yml
        :return: None
        """
        self.is_existed(key)
        self.ssh.check_call(
            "{reclass_tools} add-key {key} {value} \
            /srv/salt/reclass/classes/{path}".format(
                reclass_tools=self.reclass_tools_cmd,
                key=key,
                value=value,
                path=short_path
            ))

    def add_bool_key(self, key, value, short_path):
        """
        Shows alert if key exists

        :param key: string, parameters which will be added or updated
        :param value: value of key
        :param short_path: path to reclass yaml file.
            It takes into account default path where the reclass locates.
            May look like cluster/*/cicd/control/leader.yml
        :return: None
        """
        self.is_existed(key)
        self.ssh.check_call(
            "{reclass_tools} add-bool-key {key} {value} \
            /srv/salt/reclass/classes/{path}".format(
                reclass_tools=self.reclass_tools_cmd,
                key=key,
                value=value,
                path=short_path
            ), raise_on_err=False)

    def add_class(self, value, short_path):
        """
        Shows warning if class exists
        :param value: role to add to 'classes' parameter in the reclass
        :param short_path: path to reclass yaml file.
            It takes into account default path where the reclass locates.
            May look like cluster/*/cicd/control/leader.yml
        :return: None
        """
        if value in self.ssh.check_call(
                "{reclass_tools} get-key classes \
                /srv/salt/reclass/classes/{path} --merge".format(
                    reclass_tools=self.reclass_tools_cmd,
                    value=value,
                    path=short_path
                )):
            LOG.warning("Class {} already exists in {}".format(
                value,
                short_path
            ))

        self.ssh.check_call(
            "{reclass_tools} add-key classes {value} \
            /srv/salt/reclass/classes/{path} --merge".format(
                reclass_tools=self.reclass_tools_cmd,
                value=value,
                path=short_path
            ))
