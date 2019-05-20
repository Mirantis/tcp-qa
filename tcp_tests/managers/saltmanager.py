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

import netaddr
import pkg_resources
import yaml

from collections import defaultdict

from datetime import datetime
from pepper import libpepper
from tcp_tests.helpers import utils
from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin

LOG = logger.logger


class SaltManager(ExecuteCommandsMixin):
    """docstring for SaltManager"""

    __config = None
    __underlay = None
    _map = {
        'enforceState': 'enforce_state',
        'enforceStates': 'enforce_states',
        'runState': 'run_state',
        'runStates': 'run_states',
    }

    def __init__(self, config, underlay, host=None, port='6969',
                 username=None, password=None):
        self.__config = config
        self.__underlay = underlay
        self.__port = port
        self.__host = host
        self.__api = None
        self.__user = username or settings.SALT_USER
        self.__password = password or settings.SALT_PASSWORD
        self._salt = self

        super(SaltManager, self).__init__(config=config, underlay=underlay)

    def install(self, commands):
        # if self.__config.salt.salt_master_host == '0.0.0.0':
        #    # Temporary workaround. Underlay should be extended with roles
        #    salt_nodes = self.__underlay.node_names()
        #    self.__config.salt.salt_master_host = \
        #        self.__underlay.host_by_node_name(salt_nodes[0])

        self.execute_commands(commands=commands,
                              label="Install and configure salt")
        self.create_env_salt()
        self.create_env_jenkins_day01()
        self.create_env_jenkins_cicd()
        self.create_env_k8s()

    def change_creds(self, username, password):
        self.__user = username
        self.__password = password

    @property
    def port(self):
        return self.__port

    @property
    def host(self):
        if self.__host:
            return self.__host
        else:
            # TODO(ddmitriev): consider to add a check and raise
            # exception if 'salt_master_host' is not initialized.
            return self.__config.salt.salt_master_host

    @property
    def api(self):
        def login():
            LOG.info("Authentication in Salt API")
            self.__api.login(
                username=self.__user,
                password=self.__password,
                eauth='pam')
            return datetime.now()

        if self.__api:
            if (datetime.now() - self.__session_start).seconds < 5 * 60:
                return self.__api
            else:
                # FIXXME: Change to debug
                LOG.info("Session's expired")
                self.__session_start = login()
                return self.__api

        url = "http://{host}:{port}".format(
            host=self.host, port=self.port)
        LOG.info("Connecting to Salt API {0}".format(url))
        self.__api = libpepper.Pepper(url)
        self.__session_start = login()
        return self.__api

    def local(self, tgt, fun, args=None, kwargs=None, timeout=None):
        return self.api.local(tgt, fun, args, kwargs, timeout=timeout,
                              expr_form='compound')

    def local_async(self, tgt, fun, args=None, kwargs=None, timeout=None):
        return self.api.local_async(tgt, fun, args, kwargs, timeout=timeout)

    def lookup_result(self, jid):
        return self.api.lookup_jid(jid)

    def check_result(self, r):
        if len(r.get('return', [])) == 0:
            raise LookupError("Result is empty or absent")

        result = r['return'][0]
        if len(result) == 0:
            raise LookupError("Result is empty or absent")
        LOG.info("Job has result for %s nodes", result.keys())
        fails = defaultdict(list)
        for h in result:
            host_result = result[h]
            LOG.info("On %s executed:", h)
            if isinstance(host_result, list):
                fails[h].append(host_result)
                continue
            for t in host_result:
                task = host_result[t]
                if task['result'] is False:
                    fails[h].append(task)
                    LOG.error("%s - %s", t, task['result'])
                else:
                    LOG.info("%s - %s", t, task['result'])

        return fails if fails else None

    def enforce_state(self, tgt, state, args=None, kwargs=None, timeout=None):
        r = self.local(tgt=tgt, fun='state.sls', args=state, timeout=timeout)
        f = self.check_result(r)
        return r, f

    def enforce_states(self, tgt, state, args=None, kwargs=None, timeout=None):
        rets = []
        for s in state:
            r = self.enforce_state(tgt=tgt, state=s, timeout=timeout)
            rets.append(r)
        return rets

    def run_state(self, tgt, state, args=None, kwargs=None, timeout=None):
        return self.local(tgt=tgt, fun=state, args=args, kwargs=kwargs,
                          timeout=timeout), None

    def run_states(self, tgt, state, args=None, kwargs=None, timeout=None):
        rets = []
        for s in state:
            r = self.run_state(tgt=tgt, state=s, args=args, kwargs=kwargs,
                               timeout=timeout)
            rets.append(r)
        return rets

    def get_pillar(self, tgt, pillar):
        result = self.local(tgt=tgt, fun='pillar.get', args=pillar)
        return result['return']

    def get_single_pillar(self, tgt, pillar):
        """Get a scalar value from a single node

        :return: pillar value
        """

        result = self.get_pillar(tgt, pillar)
        nodes = result[0].keys()

        if not nodes:
            raise LookupError("No minions selected "
                              "for the target '{0}'".format(tgt))
        if len(nodes) > 1:
            raise LookupError("Too many minions selected "
                              "for the target '{0}' , expected one: {1}"
                              .format(tgt, nodes))
        return result[0][nodes[0]]

    def get_grains(self, tgt, grains):
        result = self.local(tgt=tgt, fun='grains.get', args=grains)
        return result['return']

    def get_ssh_data(self):
        """Generate ssh config for Underlay

        :param roles: list of strings
        """

        pool_name = self.__config.underlay.net_mgmt
        pool_net = netaddr.IPNetwork(self.__config.underlay.address_pools[
            self.__config.underlay.net_mgmt])
        hosts = self.local('*', 'grains.item', ['host', 'ipv4'])

        if len(hosts.get('return', [])) == 0:
            raise LookupError("Hosts is empty or absent")
        hosts = hosts['return'][0]
        if len(hosts) == 0:
            raise LookupError("Hosts is empty or absent")

        def host(minion_id, ip):
            return {
                'roles': ['salt_minion'],
                'keys': [
                    k['private'] for k in self.__config.underlay.ssh_keys
                ],
                'node_name': minion_id,
                'minion_id': minion_id,
                'host': ip,
                'address_pool': pool_name,
                'login': settings.SSH_NODE_CREDENTIALS['login'],
                'password': settings.SSH_NODE_CREDENTIALS['password']
            }

        try:
            ret = [
                host(k, next(i for i in v['ipv4'] if i in pool_net))
                for k, v in hosts.items()
                if next(i for i in v['ipv4'] if i in pool_net)]
            LOG.debug("Fetched ssh data from salt grains - {}".format(ret))
            return ret
        except StopIteration:
            msg = ("Can't match nodes ip address with network cidr\n"
                   "Managment network - {net}\n"
                   "Host with address - {host_list}".format(
                       net=pool_net,
                       host_list={k: v['ipv4'] for k, v in hosts.items()}))
            raise StopIteration(msg)

    def update_ssh_data_from_minions(self):
        """Combine existing underlay.ssh with VCP salt minions"""
        salt_nodes = self.get_ssh_data()

        for salt_node in salt_nodes:
            nodes = [n for n in self.__config.underlay.ssh
                     if salt_node['host'] == n['host']
                     and salt_node['address_pool'] == n['address_pool']]
            if nodes:
                # Assume that there can be only one node with such IP address
                # Just update minion_id for this node
                nodes[0]['minion_id'] = salt_node['minion_id']
            else:
                # New node, add to config.underlay.ssh
                self.__config.underlay.ssh.append(salt_node)

        self.__underlay.config_ssh = []
        self.__underlay.add_config_ssh(self.__config.underlay.ssh)

    def service_status(self, tgt, service):
        result = self.local(tgt=tgt, fun='service.status', args=service)
        return result['return']

    def service_restart(self, tgt, service):
        result = self.local(tgt=tgt, fun='service.restart', args=service)
        return result['return']

    def service_stop(self, tgt, service):
        result = self.local(tgt=tgt, fun='service.stop', args=service)
        return result['return']

    def cmd_run(self, tgt, cmd):
        result = self.local(tgt=tgt, fun='cmd.run', args=cmd)
        return result['return']

    @utils.retry(3, exception=libpepper.PepperException)
    def sync_time(self, tgt='*'):
        LOG.info("NTP time sync on the salt minions '{0}'".format(tgt))
        # Force authentication update on the next API access
        # because previous authentication most probably is not valid
        # before or after time sync.
        self.__api = None
        if not settings.SKIP_SYNC_TIME:
            cmd = ('service ntp stop;'
                   'if systemctl is-active --quiet maas-rackd; then'
                   '  systemctl stop maas-rackd; RACKD=true;'
                   'else'
                   '  RACKD=false;'
                   'fi;'
                   'if systemctl is-active --quiet maas-regiond; then'
                   '  systemctl stop maas-regiond; REGIOND=true;'
                   'else'
                   '  REGIOND=false;'
                   'fi;'
                   'if [ -x /usr/sbin/ntpdate ]; then'
                   '  ntpdate -s ntp.ubuntu.com;'
                   'else'
                   '  ntpd -gq;'
                   'fi;'
                   'service ntp start;'
                   'if $RACKD; then systemctl start maas-rackd; fi;'
                   'if $REGIOND; then systemctl start maas-regiond; fi;')
            self.run_state(
                tgt,
                'cmd.run', cmd)  # noqa
        new_time_res = self.run_state(tgt, 'cmd.run', 'date')
        for node_name, time in sorted(new_time_res[0]['return'][0].items()):
            LOG.info("{0}: {1}".format(node_name, time))
        self.__api = None

    def create_env_salt(self):
        """Creates static utils/env_salt file"""

        env_salt_filename = pkg_resources.resource_filename(
            settings.__name__, 'utils/env_salt')
        with open(env_salt_filename, 'w') as f:
            f.write(
                'export SALT_MASTER_IP={host}\n'
                'export SALTAPI_URL=http://{host}:{port}/\n'
                'export SALTAPI_USER="{user}"\n'
                'export SALTAPI_PASS="{password}"\n'
                'export SALTAPI_EAUTH="pam"\n'
                'echo "export SALT_MASTER_IP=${{SALT_MASTER_IP}}"\n'
                'echo "export SALTAPI_URL=${{SALTAPI_URL}}"\n'
                'echo "export SALTAPI_USER=${{SALTAPI_USER}}"\n'
                'echo "export SALTAPI_PASS=${{SALTAPI_PASS}}"\n'
                'echo "export SALTAPI_EAUTH=${{SALTAPI_EAUTH}}"\n'
                .format(host=self.host, port=self.port,
                        user=self.__user, password=self.__password)
            )

    def create_env_jenkins_day01(self):
        """Creates static utils/env_jenkins_day01 file"""

        env_jenkins_day01_filename = pkg_resources.resource_filename(
            settings.__name__, 'utils/env_jenkins_day01')

        tgt = 'I@docker:client:stack:jenkins and cfg01*'
        jenkins_params = self.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master")
        jenkins_port = jenkins_params['port']
        jenkins_user = jenkins_params['username']
        jenkins_pass = jenkins_params['password']

        with open(env_jenkins_day01_filename, 'w') as f:
            f.write(
                'export JENKINS_URL=http://{host}:{port}\n'
                'export JENKINS_USER={user}\n'
                'export JENKINS_PASS={password}\n'
                'export JENKINS_START_TIMEOUT=60\n'
                'export JENKINS_BUILD_TIMEOUT=1800\n'
                'echo "export JENKINS_URL=${{JENKINS_URL}}'
                '  # Jenkins API URL"\n'
                'echo "export JENKINS_USER=${{JENKINS_USER}}'
                '  # Jenkins API username"\n'
                'echo "export JENKINS_PASS=${{JENKINS_PASS}}'
                '  # Jenkins API password or token"n\n'
                'echo "export JENKINS_START_TIMEOUT=${{JENKINS_START_TIMEOUT}}'
                '  # Timeout waiting for job in queue to start building"\n'
                'echo "export JENKINS_BUILD_TIMEOUT=${{JENKINS_BUILD_TIMEOUT}}'
                '  # Timeout waiting for building job to complete"\n'
                .format(host=self.host, port=jenkins_port,
                        user=jenkins_user, password=jenkins_pass)
            )

    def create_env_jenkins_cicd(self):
        """Creates static utils/env_jenkins_cicd file"""

        env_jenkins_cicd_filename = pkg_resources.resource_filename(
            settings.__name__, 'utils/env_jenkins_cicd')
        domain_name = self.get_single_pillar(
            tgt="I@salt:master", pillar="_param:cluster_domain")
        LOG.info("Domain: {}".format(domain_name))
        cid01 = 'cid01.' + domain_name
        LOG.info("{}".format(cid01))
        command = "reclass -n {}".format(cid01)
        LOG.info("{}".format(command))
        cfg = self.__underlay.get_target_node_names('cfg01')[0]
        LOG.info("cfg node name:{}".format(cfg))
        output = self.__underlay.check_call(
            node_name=cfg,
            cmd=command)
        result = yaml.load(output.stdout_str)
        jenkins_params = result.get(
            'parameters', {}).get(
            'jenkins', {}).get(
            'client', {}).get(
            'master', {})
        if not jenkins_params:
            return
        jenkins_host = jenkins_params['host']
        LOG.info("jenkins_host: {}".format(jenkins_host))
        jenkins_port = jenkins_params['port']
        LOG.info("jenkins_port: {}".format(result))
        jenkins_user = jenkins_params['username']
        LOG.info("jenkins_user: {}".format(result))
        jenkins_pass = jenkins_params['password']
        LOG.info("jenkins_pass: {}".format(result))

        with open(env_jenkins_cicd_filename, 'w') as f:
            f.write(
                'export JENKINS_URL=http://{host}:{port}\n'
                'export JENKINS_USER={user}\n'
                'export JENKINS_PASS={password}\n'
                'export JENKINS_START_TIMEOUT=60\n'
                'export JENKINS_BUILD_TIMEOUT=1800\n'
                'echo "export JENKINS_URL=${{JENKINS_URL}}'
                '  # Jenkins API URL"\n'
                'echo "export JENKINS_USER=${{JENKINS_USER}}'
                '  # Jenkins API username"\n'
                'echo "export JENKINS_PASS=${{JENKINS_PASS}}'
                '  # Jenkins API password or token"n\n'
                'echo "export JENKINS_START_TIMEOUT=${{JENKINS_START_TIMEOUT}}'
                '  # Timeout waiting for job in queue to start building"\n'
                'echo "export JENKINS_BUILD_TIMEOUT=${{JENKINS_BUILD_TIMEOUT}}'
                '  # Timeout waiting for building job to complete"\n'
                .format(host=jenkins_host, port=jenkins_port,
                        user=jenkins_user, password=jenkins_pass)
            )

    def create_env_k8s(self):
        """Creates static utils/env_k8s file"""

        env_k8s_filename = pkg_resources.resource_filename(
            settings.__name__, 'utils/env_k8s')
        domain_name = self.get_single_pillar(
            tgt="I@salt:master", pillar="_param:cluster_domain")
        LOG.info("Domain: {}".format(domain_name))
        ctl01 = 'ctl01.' + domain_name
        LOG.info("{}".format(ctl01))
        command = "reclass -n {}".format(ctl01)
        LOG.info("{}".format(command))
        cfg = self.__underlay.get_target_node_names('cfg01')[0]
        LOG.info("cfg node name:{}".format(cfg))
        output = self.__underlay.check_call(
            node_name=cfg,
            cmd=command)
        result = yaml.load(output)
        haproxy_params = result.get(
            'parameters', {}).get(
            'haproxy', {}).get(
            'proxy', {}).get(
            'listen', {}).get(
            'k8s_secure', {}).get(
            'binds', {})
        if not haproxy_params:
            return
        k8s_params = result.get(
            'kubernetes', {}).get(
            'master', {}).get(
            'admin', {})
        if not k8s_params:
            return
        kube_host = haproxy_params['address']
        LOG.info("kube_host: {}".
                 format(kube_host))
        kube_apiserver_port = haproxy_params['port']
        LOG.info("kube_apiserver_port: {}".
                 format(kube_apiserver_port))
        kubernetes_admin_user = k8s_params['username']
        LOG.info("kubernetes_admin_user: {}".
                 format(kubernetes_admin_user))
        kubernetes_admin_password = k8s_params['password']
        LOG.info("kubernetes_admin_password: {}".
                 format(kubernetes_admin_password))

        with open(env_k8s_filename, 'w') as f:
            f.write(
                'export kube_host={host}\n'
                'export kube_apiserver_port={port}\n'
                'export kubernetes_admin_user={user}\n'
                'export kubernetes_admin_password={password}\n'
                'echo "export kube_host=${{kube_host}}'
                '  # Kube API host"\n'
                'echo "export kube_apiserver_port=${{kube_apiserver_port}}'
                '  # Kube API port"\n'
                'echo "export kubernetes_admin_user=${{kubernetes_admin_user}}'
                '  # Kube API username"\n'
                'echo "export kubernetes_admin_password='
                '${{kubernetes_admin_password}}  # Kube API password"n\n'
                .format(host=kube_host, port=kube_apiserver_port,
                        user=kubernetes_admin_user,
                        password=kubernetes_admin_password)
            )
