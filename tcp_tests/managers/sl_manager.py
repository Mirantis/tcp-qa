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
from tcp_tests.managers.clients.prometheus import prometheus_client
from tcp_tests import logger

LOG = logger.logger


class SLManager(ExecuteCommandsMixin):
    """docstring for OpenstackManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        self._p_client = None
        super(SLManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands, label='Install SL services'):
        self.execute_commands(commands, label=label)
        self.__config.stack_light.sl_installed = True
        self.__config.stack_light.sl_vip_host = self.get_sl_vip()

    def get_sl_vip(self):
        tgt = 'I@prometheus:server:enabled:True'
        pillar = 'keepalived:cluster:instance:prometheus_server_vip:address'
        sl_vip_address_pillars = self._salt.get_pillar(tgt=tgt,
                                                       pillar=pillar)
        sl_vip_ip = set([ip
                         for item in sl_vip_address_pillars
                         for node, ip in item.items() if ip])
        if not sl_vip_ip:
            pillar = 'keepalived:cluster:instance:VIP:address'
            sl_vip_address_pillars = self._salt.get_pillar(tgt=tgt,
                                                           pillar=pillar)
            sl_vip_ip = set([ip
                             for item in sl_vip_address_pillars
                             for node, ip in item.items() if ip])
        if not sl_vip_ip:
            pillar = 'keepalived:cluster:instance:stacklight_monitor_vip:address'
            sl_vip_address_pillars = self._salt.get_pillar(tgt=tgt,
                                                           pillar=pillar)
            sl_vip_ip = set([ip
                             for item in sl_vip_address_pillars
                             for node, ip in item.items() if ip])
        assert len(sl_vip_ip) == 1, (
            "SL VIP not found or found more than one SL VIP in pillars:{0}, "
            "expected one!").format(sl_vip_ip)
        sl_vip_ip_host = sl_vip_ip.pop()
        return sl_vip_ip_host

    @property
    def api(self):
        if self._p_client is None:
            self._p_client = prometheus_client.PrometheusClient(
                host=self.__config.stack_light.sl_vip_host,
                port=self.__config.stack_light.sl_prometheus_port,
                proto=self.__config.stack_light.sl_prometheus_proto)
        return self._p_client

    def get_monitoring_nodes(self):
        return [node_name for node_name
                in self.__underlay.node_names() if 'mon' in node_name]

    def get_service_info_from_node(self, node_name):
        service_stat_dict = {}
        with self.__underlay.remote(node_name=node_name) as node_remote:
            result = node_remote.execute(
                "docker service ls --format '{{.Name}}:{{.Replicas}}'")
            LOG.debug("Service ls result {0} from node {1}".format(
                result['stdout'], node_name))
            for line in result['stdout']:
                tmp = line.split(':')
                service_stat_dict.update({tmp[0]: tmp[1]})
        return service_stat_dict

    def run_sl_functional_tests(self, node_to_run, tests_path,
                                test_to_run, skip_tests):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_to_run in node_name]
        cmd = (". venv-stacklight-pytest/bin/activate;"
               "cd {0}; "
               "export VOLUME_STATUS='available';"
               "pytest -k {1} {2}".format(
                   tests_path,
                   "'not " + skip_tests + "'" if skip_tests else '',
                   test_to_run))

        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            result = node_remote.execute(cmd, verbose=True)
            LOG.debug("Test execution result is {}".format(result))
        return result

    def run_sl_tests_json(self, node_to_run, tests_path,
                          test_to_run, skip_tests):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_to_run in node_name]
        cmd = (". venv-stacklight-pytest/bin/activate;"
               "cd {0}; "
               "export VOLUME_STATUS='available';"
               "pip install pytest-json;"
               "pytest --json=report.json -k {1} {2}".format(
                   tests_path,
                   "'not " + skip_tests + "'" if skip_tests else '',
                   test_to_run))

        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            node_remote.execute(cmd, verbose=True)
            res = node_remote.check_call('cd {0}; cat report.json'.format(
                tests_path), verbose=True)
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

    def check_docker_services(self, nodes, expected_services):
        """Check presense of the specified docker services on all the nodes
        :param nodes: list of strings, names of nodes to check
        :param expected_services: list of strings, names of services to find
        """
        for node in nodes:
            services_status = self.get_service_info_from_node(node)
            assert set(services_status) >= set(expected_services), \
                'Some services are missed on node {0}. ' \
                'Current service list: {1}\nExpected service list: {2}' \
                .format(node, services_status, expected_services)
            for service in expected_services:
                assert service in services_status,\
                    'Missing service {0} in {1}'.format(service,
                                                        services_status)
                assert '0' not in services_status.get(service),\
                    'Service {0} failed to start'.format(service)

    @decorators.retry(AssertionError, count=10, delay=5)
    def check_prometheus_targets(self, nodes):
        """Check the status for Prometheus targets
        :param nodes: list of strings, names of nodes with keepalived VIP
        """
        prometheus_client = self.api
        current_targets = prometheus_client.get_targets()

        LOG.debug('Current targets after install {0}'
                  .format(current_targets))
        # Assert that targets are up
        for entry in current_targets:
            assert 'up' in entry['health'], \
                'Next target is down {}'.format(entry)

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

    def post_data_into_influx(self, node_sub_name):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_sub_name in node_name]
        vip = self.get_sl_vip()
        cmd = ("curl -POST 'http://{0}:8086/write?db=lma' -u "
               "lma:lmapass --data-binary 'mymeas value=777'".format(vip))
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            res = node_remote.execute(cmd)
            assert res['exit_code'] == 0, (
                'Unexpected exit code for command {0}, '
                'current result {1}'.format(cmd, res))

    def check_data_in_influxdb(self, node_sub_name):
        target_node_name = [node_name for node_name
                            in self.__underlay.node_names()
                            if node_sub_name in node_name]
        vip = self.get_sl_vip()
        cmd = ("influx -host {0} -port 8086 -database lma  "
               "-username lma -password lmapass -execute "
               "'select * from mymeas' -precision rfc3339;".format(vip))
        with self.__underlay.remote(node_name=target_node_name[0]) \
                as node_remote:
            LOG.debug("Run {0} on the node {1}".format(
                cmd, target_node_name[0]))
            res = node_remote.execute(cmd)
            assert res['exit_code'] == 0, (
                'Unexpected exit code for command {0}, '
                'current result {1}'.format(cmd, res))
            if res['stdout']:
                return res['stdout'][0].rstrip()
            else:
                return ''

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
