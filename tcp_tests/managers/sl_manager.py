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

from tcp_tests.managers.execute_commands import ExecuteCommandsMixin
from tcp_tests.managers.clients.prometheus import prometheus_client


class SLManager(ExecuteCommandsMixin):
    """docstring for OpenstackManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        self.p_client = None
        super(SLManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install SL services')
        self.__config.stack_light.sl_installed = True
        self.__config.stack_light.sl_vip_host = self.get_sl_vip()

    def get_sl_vip(self):
        sl_vip_address_pillars = self._salt.get_pillar(
            tgt='I@keepalived:cluster:enabled:true and not ctl*',
            pillar='keepalived:cluster:instance:prometheus_server_vip:address')
        sl_vip_ip = set([ip
                            for item in sl_vip_address_pillars
                            for node,ip in item.items() if ip])
        assert len(sl_vip_ip) == 1, (
            "Found more than one SL VIP in pillars:{0}, "
            "expected one!").format(sl_vip_ip)
        sl_vip_ip_host = sl_vip_ip.pop()
        return sl_vip_ip_host

    @property
    def api(self):
        if self.p_client is None:
            self._p_client = prometheus_client.PrometheusClient(
                host=self.__config.stack_light.sl_vip_host,
                port=self.__config.stack_light.sl_prometheus_port,
                proto=self.__config.stack_light.sl_prometheus_proto)
        return self.p_client
