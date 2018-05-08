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

from tcp_tests.helpers import exceptions
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin
from tcp_tests import logger

LOG = logger.logger


class CommonServicesManager(ExecuteCommandsMixin):
    """docstring for CommonServicesManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt=None):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        super(CommonServicesManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install common services')
        self.__config.common_services.common_services_installed = True

    def get_keepalived_vip_minion_id(self, vip):
        """Get minion ID where keepalived VIP is at the moment"""
        tgt = 'I@keepalived:cluster:enabled:True'
        grains = 'ip_interfaces'
        # Refresh grains first
        self._salt.run_state(tgt, 'saltutil.refresh_grains')
        # Get grains
        result = self._salt.get_grains(tgt=tgt, grains=grains)[0]
        minion_ids = [
            minion_id for minion_id, interfaces in result.items()
            for interface, ips in interfaces.items()
            for ip in ips
            if ip == vip
        ]
        LOG.debug("VIP '{0}' found on minions {1}".format(vip, minion_ids))
        if len(minion_ids) != 1:
            raise Exception("VIP {0} is expected on a single node. Actual "
                            "nodes with VIP: {1}".format(vip, minion_ids))
        return minion_ids[0]

    def get_keepalived_vips(self):
        tgt = 'I@keepalived:cluster:enabled:True'
        pillar = 'keepalived:cluster:instance'
        return self._salt.get_pillar(tgt=tgt, pillar=pillar)[0]

    def check_keepalived_pillar(self):
        """Check the keepalived pillars for VIPs

        Check for:
        - the same VIP is used for the same 'virtual_router_id'
        - the same password is used for the same 'virtual_router_id'
        - no 'virtual_router_id' or VIP doubles in different
          keepalived instances on the same node
        - no 'priority' doubles inside the same 'virtual_router_id'
          on different nodes

        :param pillar_vips: dict {
            <minion_id>: {
                <keepalived instance>: {
                    <address>: str,
                    <password>: str,
                    <virtual_router_id>: int,
                    <priority>: int
                },
                ...
            },
        }
        :return dict: {
            <str:vip1> : {
                'instance_name': <str>
                'virtual_router_id': <int>,
                'password': <str>,
                'nodes' : {<str:node1>: <int:priority>,
                           <str:node2>: <int:priority>,
                           ...},
            },
            <str:vip2> : { ...
            },
        }
        """

        def check_single_address(vips, minion_id, instance, data):
            for vip in vips:
                if vips[vip]['virtual_router_id'] == data['virtual_router_id']\
                        and (vip != data['address'] or
                             vips[vip]['instance_name'] != instance):
                    message = (
                        "'virtual_router_id': {0} for keepalived instance "
                        "{1}: {2} is already used for {3}: {4} on nodes {5}"
                        .format(data['virtual_router_id'],
                                instance, data['address'],
                                vips[vip]['instance_name'],
                                vip,
                                vips[vip]['nodes'].keys())
                    )
                    raise exceptions.SaltPillarError(
                        minion_id,
                        'keepalived:cluster:instance',
                        message)

        def check_single_router_id(vips, minion_id, instance, data):
            for vip in vips:
                if vips[vip]['virtual_router_id'] != data['virtual_router_id']\
                        and vip == data['address']:
                    message = (
                        "'virtual_router_id': {0} for keepalived instance "
                        "{1}: {2} is not the same as for {3}: {4} on nodes {5}"
                        .format(data['virtual_router_id'],
                                instance, data['address'],
                                vips[vip]['instance_name'],
                                vip,
                                vips[vip]['nodes'].keys())
                    )
                    raise exceptions.SaltPillarError(
                        minion_id,
                        'keepalived:cluster:instance',
                        message)

        pillar_vips = self.get_keepalived_vips()
        vips = {}
        for minion_id in pillar_vips:
            for instance, data in pillar_vips[minion_id].items():
                address = data['address']
                password = data['password']
                virtual_router_id = data['virtual_router_id']
                priority = data['priority']

                if address not in vips:
                    # Check that there is the same VIP
                    # for the same virtual_router_id
                    check_single_address(vips, minion_id, instance, data)

                    # Add new VIP
                    vips[address] = {
                        'instance_name': instance,
                        'virtual_router_id': virtual_router_id,
                        'password': password,
                        'nodes': {
                            minion_id: priority,
                        }
                    }
                else:
                    # Check that there is the same virtual_router_id
                    # for the same VIP
                    check_single_router_id(vips, minion_id, instance, data)
                    if vips[address]['password'] != password:
                        message = (
                            "'password': {0} for keepalived instance "
                            "{1}: {2} is not the same as for {3}: {4} on "
                            "nodes {5}".format(data['password'],
                                               instance, data['address'],
                                               vips[address]['instance_name'],
                                               address,
                                               vips[address]['nodes'].keys())
                        )
                        raise exceptions.SaltPillarError(
                            minion_id,
                            'keepalived:cluster:instance',
                            message)

                    # keepalived 'priority' can be the same on multiple nodes
                    if any([priority == prio
                            for node, prio in vips[address]['nodes'].items()]):
                        message = (
                            "'priority': {0} for keepalived instance "
                            "{1}: {2} is the same as for {3}: {4} on "
                            "nodes {5}".format(data['priority'],
                                               instance, data['address'],
                                               vips[address]['instance_name'],
                                               address,
                                               vips[address]['nodes'].keys())
                        )
                        LOG.warning("On {0}, {1}".format(minion_id, message))

                    # Add data to the vips
                    vips[address]['nodes'][minion_id] = priority

        LOG.debug("keepalived pillars check passed: {0}".format(vips))
        return vips

    def get_haproxy_status(self, tgt):
        """Get haproxy status for all backends on a specified minion"""
        cmd = ("echo 'show stat' | "
               "socat 'UNIX-CONNECT:/run/haproxy/admin.sock' STDIO")
        # Refresh grains first
        res = self._salt.run_state(tgt, 'cmd.run', cmd)
        output = res[0]['return'][0]
        assert len(output.keys()) == 1, "Please specify a single minion in tgt"
        minion_id = output.keys()[0]

        haproxy_status = {}
        for line in output[minion_id].splitlines():
            if line.startswith("#"):
                continue
            status = line.split(",")
            pxname = status[0]
            svname = status[1]
            if pxname not in haproxy_status:
                haproxy_status[pxname] = {}
            haproxy_status[pxname][svname] = {
                'scur': status[4],     # sessions current
                'smax': status[5],     # sessions max
                'status': status[17],  # status: UP or DOWN
                'rate': status[33],    # sessions rate
            }
        LOG.debug("Haproxy status: \n{0}".format(haproxy_status))
        return haproxy_status
