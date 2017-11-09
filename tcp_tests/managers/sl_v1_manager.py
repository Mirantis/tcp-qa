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
import json
import os

from devops.helpers import decorators

from tcp_tests.managers.execute_commands import ExecuteCommandsMixin
from tcp_tests import logger

LOG = logger.logger


class SLV1Manager(ExecuteCommandsMixin):
    """docstring for OpenstackManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        self._p_client = None
        super(SLV1Manager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install SL_v1 services')
        self.__config.stack_light_v1.sl_v1_installed = True
        self.__config.stack_light_v1.sl_v1_vip_host = self.get_sl_v1_vip()

    def upgrade(self, commands):
        self.execute_commands(commands,
                              label='Upgrade SL_v1 services')
        self.__config.sl_v1_upgrade.sl_v1_upgraded = True

    def get_sl_v1_vip(self):
        sl_vip_address_pillars = self._salt.get_pillar(
            tgt='mon*',
            pillar='keepalived:cluster:instance:VIP:address')
        sl_vip_ip = set([ip
                         for item in sl_vip_address_pillars
                         for node, ip in item.items() if ip])
        assert len(sl_vip_ip) == 1, (
            "SL VIP not found or found more than one SL VIP in pillars:{0}, "
            "expected one!").format(sl_vip_ip)
        sl_vip_ip_host = sl_vip_ip.pop()
        return sl_vip_ip_host

    def get_monitoring_nodes(self):
        return [node_name for node_name
                in self.__underlay.node_names() if 'mon' in node_name]

    def run_sl_functional_tests(self, node_to_run, tests_path,
                                test_to_run, skip_tests):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_to_run in node_name]
        if skip_tests:
            cmd = ("cd {0}; "
                   "export VOLUME_STATUS='available'; "
                   "pytest -k 'not {1}' {2}".format(
                       tests_path, skip_tests, test_to_run))
        else:
            cmd = ("cd {0}; "
                   "export VOLUME_STATUS='available'; "
                   "pytest -k {1}".format(tests_path, test_to_run))
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            result = node_remote.execute(cmd)
            LOG.debug("Test execution result is {}".format(result))
        return result

    def run_sl_tests_json(self, node_to_run, tests_path,
                          test_to_run, skip_tests):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_to_run in node_name]
        if skip_tests:
            cmd = ("cd {0}; "
                   "export VOLUME_STATUS='available'; "
                   "pytest  --json=report.json -k 'not {1}' {2}".format(
                       tests_path, skip_tests, test_to_run))
        else:
            cmd = ("cd {0}; "
                   "export VOLUME_STATUS='available'; "
                   "pytest --json=report.json -k {1}".format(
                       tests_path, test_to_run))
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            node_remote.execute('pip install pytest-json')
            node_remote.execute(cmd)
            res = node_remote.execute('cd {0}; cat report.json'.format(
                tests_path))
            LOG.debug("Test execution result is {}".format(res['stdout']))
            result = json.loads(res['stdout'][0])
        return result['report']['tests']

    def download_sl_test_report(self, stored_node, file_path):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if stored_node in node_name]
        with self.__underlay.remote(node_name=target_node_name[0]) as r:
            r.download(
                destination=file_path,
                target=os.getcwd())


    def kill_sl_service_on_node(self, node_sub_name, service_name):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_sub_name in node_name]
        cmd = 'kill -9 $(pidof {0})'.format(service_name)
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            res = node_remote.execute(cmd)
            LOG.debug("Test execution result is {}".format(res))
            assert res['exit_code'] == 0, (
                'Unexpected exit code for command {0}, '
                'current result {1}'.format(cmd, res))

    def stop_sl_service_on_node(self, node_sub_name, service_name):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_sub_name in node_name]
        cmd = 'systemctl stop {}'.format(service_name)
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            res = node_remote.execute(cmd)
            LOG.debug("Test execution result is {}".format(res))
            assert res['exit_code'] == 0, (
                'Unexpected exit code for command {0}, '
                'current result {1}'.format(cmd, res))

    def start_service(self, node_sub_name, service_name):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_sub_name in node_name]
        cmd = 'systemctl start {0}'.format(service_name)
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            res = node_remote.execute(cmd)
            assert res['exit_code'] == 0, (
                'Unexpected exit code for command {0}, '
                'current result {1}'.format(cmd, res))
