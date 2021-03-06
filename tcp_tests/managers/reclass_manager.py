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

        reclass_node = [node_name
                        for node_name in self.__underlay.node_names()
                        if self.tgt in node_name]
        self.ssh = self.__underlay.remote(node_name=reclass_node[0])

        super(ReclassManager, self).__init__(config=config, underlay=underlay)

    def check_existence(self, key):
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
        self.check_existence(key)
        self.ssh.check_call(
            "{reclass_tools} add-key {key} {value} \
            /srv/salt/reclass/classes/{path}".format(
                reclass_tools=self.reclass_tools_cmd,
                key=key,
                value=value,
                path=short_path
            ))

    def get_key(self, key, file_name):
        """Find a key in a YAML

        :param key: string, parameter to add
        :param file_name: name of YAML file to find a key
        :return: str, key if found
        """
        request_key = self.ssh.check_call(
            "{reclass_tools} get-key {key} /srv/salt/reclass/*/{file_name}".
            format(reclass_tools=self.reclass_tools_cmd,
                   key=key,
                   file_name=file_name))['stdout']

        # Reclass-tools returns result to stdout, so we get it as
        #     ['\n',
        #      '---\n',
        #      '# Found parameters._param.jenkins_pipelines_branch in \
        #          /srv/salt/reclass/classes/cluster/../infra/init.yml\n',
        #      'release/proposed/2019.2.0\n',
        #      '...\n',
        #      '\n']
        # So we have no chance to get value without dirty code like `stdout[3]`

        LOG.info("From reclass.get_key {}".format(request_key))
        if len(request_key) < 4:
            assert "Can't find {key} in {file_name}. Got stdout {stdout}".\
                format(
                    key=key,
                    file_name=file_name,
                    stdout=request_key
                )
        value = request_key[3].strip('\n')
        LOG.info("From reclass.get_key {}".format(value))
        return value

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
        self.check_existence(key)
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
                /srv/salt/reclass/classes/{path}".format(
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

    def delete_key(self, key, short_path):
        """
        Remove key from the provided file

        :param value: string, parameter which will be deleted
        :param short_path: string,, path to reclass yaml file.
            It takes into account default path where the reclass locates.
            May look like cluster/*/cicd/control/leader.yml
        :return: None
        """
        self.ssh.check_call(
            "{reclass_tools} del-key {key} \
            /srv/salt/reclass/classes/{path}".format(
                reclass_tools=self.reclass_tools_cmd,
                key=key,
                path=short_path
            ))
