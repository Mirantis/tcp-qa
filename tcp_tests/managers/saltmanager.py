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
# import time

from collections import defaultdict

from datetime import datetime
from pepper.libpepper import Pepper
from tcp_tests import settings
from tcp_tests import logger
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin

LOG = logger.logger


class SaltManager(ExecuteCommandsMixin):
    """docstring for SaltManager"""

    _config = None
    _underlay = None
    _map = {
        'enforceState': 'enforce_state',
        'enforceStates': 'enforce_states',
        'runState': 'run_state',
        'runStates': 'run_states',
    }

    def __init__(self, config, underlay, host=None, port='6969'):
        self._config = config
        self._underlay = underlay
        self._port = port
        self._host = host
        self._api = None
        self._user = settings.SALT_USER
        self._password = settings.SALT_PASSWORD
        self._salt = self

        super(SaltManager, self).__init__()

    def install(self, commands):
        if commands[0].get('do'):
            self.install2(commands)
        else:
            self.install1(commands)

    def install1(self, commands):
        if self._config.salt.salt_master_host == '0.0.0.0':
            # Temporary workaround. Underlay should be extended with roles
            salt_nodes = self._underlay.node_names()
            self._config.salt.salt_master_host = \
                self._underlay.host_by_node_name(salt_nodes[0])

        # self._underlay.execute_commands(commands=commands,
        #                                  label="Install and configure salt")
        self.execute_commands(commands=commands,
                              label="Install and configure salt")

    def install2(self, commands):
        if self._config.salt.salt_master_host == '0.0.0.0':
            # Temporary workaround. Underlay should be extended with roles
            salt_nodes = self._underlay.node_names()
            self._config.salt.salt_master_host = \
                self._underlay.host_by_node_name(salt_nodes[0])

        # self.run_commands(commands=commands,
        #                   label="Install and configure salt")
        self.execute_commands(commands=commands,
                              label="Install and configure salt")

    @property
    def port(self):
        return self._port

    @property
    def host(self):
        if self._host:
            return self._host
        elif self._config.salt.salt_master_host == '0.0.0.0':
            # Temporary workaround. Underlay should be extended with roles
            salt_nodes = self._underlay.node_names()
            self._config.salt.salt_master_host = \
                self._underlay.host_by_node_name(salt_nodes[0])

        return self._config.salt.salt_master_host

    @property
    def api(self):
        def login():
            LOG.info("Authentication in Salt API")
            self._api.login(
                username=self._user,
                password=self._password,
                eauth='pam')
            return datetime.now()

        if self._api:
            if (datetime.now() - self.__session_start).seconds < 5 * 60:
                return self._api
            else:
                # FIXXME: Change to debug
                LOG.info("Session's expired")
                self.__session_start = login()
                return self._api

        LOG.info("Connect to Salt API")
        url = "http://{host}:{port}".format(
            host=self.host, port=self.port)
        self._api = Pepper(url)
        self.__session_start = login()
        return self._api

    def local(self, tgt, fun, args=None, kwargs=None):
        return self.api.local(tgt, fun, args, kwargs, expr_form='compound')

    def local_async(self, tgt, fun, args=None, kwargs=None):
        return self.api.local_async(tgt, fun, args, kwargs)

    def lookup_result(self, jid):
        return self.api.lookup_jid(jid)

    def check_result(self, r):
        if len(r.get('return', [])) == 0:
            raise LookupError("Result is empty or absent")

        result = r['return'][0]
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

    def enforce_state(self, tgt, state, args=None, kwargs=None):
        r = self.local(tgt=tgt, fun='state.sls', args=state)
        f = self.check_result(r)
        return r, f

    def enforce_states(self, tgt, state, args=None, kwargs=None):
        rets = []
        for s in state:
            r = self.enforce_state(tgt=tgt, state=s)
            rets.append(r)
        return rets

    def run_state(self, tgt, state, args=None, kwargs=None):
        return self.local(tgt=tgt, fun=state, args=args, kwargs=kwargs), None

    def run_states(self, tgt, state, args=None, kwargs=None):
        rets = []
        for s in state:
            r = self.run_state(tgt=tgt, state=s, args=args, kwargs=kwargs)
            rets.append(r)
        return rets
