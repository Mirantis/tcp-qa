#    Copyright 2018 Mirantis, Inc.
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

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests import settings


LOG = logger.logger

TEMPEST_CFG_DIR = '/tmp/test'


class RuntestManager(object):
    """Helper manager for execution tempest via runtest-formula"""

    image_name = settings.TEMPEST_IMAGE
    image_version = settings.TEMPEST_IMAGE_VERSION
    container_name = 'run-tempest-ci'
    master_host = "cfg01"
    class_name = "runtest"
    run_cmd = '/bin/bash -c "run-tempest"'

    def __init__(self, config, underlay, salt_api, cluster_name,
                 domain_name, tempest_threads,
                 tempest_pattern=settings.TEMPEST_PATTERN,
                 tempest_extra_args=settings.TEMPEST_EXTRA_ARGS,
                 run_cmd=None):
        self.__config = config
        self.underlay = underlay
        self.__salt_api = salt_api
        self.cluster_name = cluster_name
        self.domain_name = domain_name
        self.tempest_threads = tempest_threads
        self.tempest_pattern = tempest_pattern
        self.tempest_extra_args = tempest_extra_args
        self.run_cmd = run_cmd or self.run_cmd
        self.master_name = self.underlay.get_target_node_names(
            self.master_host)[0]
        self.master_minion = self.underlay.get_target_minion_ids(
            self.master_host)[0]
        self.__target_name = None
        self.__target_minion = None

    @property
    def salt_api(self):
        return self.__salt_api

    @property
    def target_name(self):
        if not self.__target_name:
            target_host = self.__salt_api.get_single_pillar(
                tgt=self.master_minion,
                pillar="runtest:tempest:test_target")
            if target_host[-1] == "*":
                target_host = target_host[:-1]
            self.__target_name = self.underlay.get_target_node_names(
                target_host)[0]
        return self.__target_name

    @property
    def target_minion(self):
        if not self.__target_minion:
            target_host = self.__salt_api.get_single_pillar(
                tgt=self.master_minion,
                pillar="runtest:tempest:test_target")
            if target_host[-1] == "*":
                target_host = target_host[:-1]
            self.__target_minion = self.underlay.get_target_minion_ids(
                target_host)[0]
        return self.__target_minion

    def fetch_arficats(self, username=None, file_format='xml'):
        with self.underlay.remote(node_name=self.target_name,
                                  username=None) as tgt:
            result = tgt.execute('find {} -name "report_*.{}"'.format(
                TEMPEST_CFG_DIR, file_format))
            LOG.debug("Find result {0}".format(result))
            assert len(result['stdout']) > 0, ('No report found, please check'
                                               ' if test run was successful.')
            report = result['stdout'][0].rstrip()
            LOG.debug("Found files {0}".format(report))
            tgt.download(
                destination=report,  # noqa
                target=os.getcwd())

    def save_runtime_logs(self, logs=None, inspect=None):
        if logs:
            with open("{path}/{target}_tempest_run.log".format(
                    path=settings.LOGS_DIR,
                    target=self.target_name), 'w') as f:
                LOG.info("Save tempest console log")
                container_log = logs
                f.write(container_log.encode('ascii', 'ignore'))

        if inspect:
            with open("{path}/{target}_tempest_container_info.json.log".format(
                    path=settings.LOGS_DIR,
                    target=self.target_name), 'w') as f:
                LOG.info("Save tempest container inspect data")

                container_inspect = json.dumps(inspect,
                                               indent=4, sort_keys=True)
                f.write(container_inspect)

    def prepare(self):
        salt_call_cmd = "salt-call -l info --hard-crash --state-output=mixed "
        barbican_integration = self.__salt_api.get_single_pillar(
            tgt="ctl01*",
            pillar="_param:barbican_integration_enabled")

        LOG.info("Barbican integration {0}".format(barbican_integration))
        commands = [
            {
                'description': ("Install docker-ce package and "
                                "enable packets forwarding"),
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " pkg.install docker-ce && " +
                        " iptables --policy FORWARD ACCEPT")},
            {
                'description': "Install PyPI docker package",
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " pip.install setuptools && " +
                        salt_call_cmd + " pip.install docker")},
            {
                'description': "Generate config for Tempest",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        "salt-run state.orchestrate " +
                        "runtest.orchestrate.tempest")},
        ]

        if barbican_integration:
            commands.append({
                'description': "Configure barbican",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd +
                        " state.sls barbican.client && " +
                        salt_call_cmd +
                        " state.sls runtest.test_accounts" +
                        salt_call_cmd +
                        " state.sls runtest.barbican_sign_image")},
            )

        self.__salt_api.execute_commands(commands=commands,
                                         label="Prepare for Tempest")

    def run_tempest(self, timeout=600):
        tgt = self.target_minion
        image_nameversion = "{}:{}".format(self.image_name, self.image_version)

        docker_args = (
            " -t"
            " --net host"
            " --name {container_name}"
            " -e ARGS=\"-r {tempest_pattern}"
            " -w {tempest_threads} {tempest_extra_args}\""
            " -v {cfg_dir}/tempest.conf:/etc/tempest/tempest.conf"
            " -v /tmp/:/tmp/"
            " -v {cfg_dir}:/root/tempest"
            " -v /etc/ssl/certs/:/etc/ssl/certs/"
            " -d"
            " {image_nameversion} {run_cmd}"
            .format(
                container_name=self.container_name,
                image_nameversion=image_nameversion,
                tempest_pattern=self.tempest_pattern,
                tempest_threads=self.tempest_threads,
                tempest_extra_args=self.tempest_extra_args,
                cfg_dir=TEMPEST_CFG_DIR,
                run_cmd=self.run_cmd,
            ))

        commands = [
            {
                'description': "Run Tempest tests {0}".format(
                    image_nameversion),
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        " docker rm --force {container_name} || true;"
                        " docker run {docker_args}"
                        .format(container_name=self.container_name,
                                docker_args=docker_args)),
                'timeout': timeout},
        ]

        self.__salt_api.execute_commands(commands=commands,
                                         label="Run Tempest tests")

        def simplify_salt_api_return(api_return, only_first_match=True):
            """
                Salt API always returns a dict with one key as 'return'
                and value as a list with dict. For example:
            For single node:
                api.local('cfg01*', 'test.ping', expr_form='compound')
                {u'return':[{u'cfg01.cookied-cicd-queens-dvr-sl.local':True}]}
            For multinode:
                api.local('ctl*', 'test.ping', expr_form='compound')
                {u'return': [{u'ctl01.cookied-cicd-queens-dvr-sl.local': True,
                 u'ctl02.cookied-cicd-queens-dvr-sl.local': True,
                u'ctl03.cookied-cicd-queens-dvr-sl.local': True}]}
            When wrong function is given:
                api.local('ctl01*', 'wrong_func', expr_form='compound')
                {u'return': [{u'ctl01.cookied-cicd-queens-dvr-sl.local':
                 u"'wrong_func' is not available."}]}
            Empty return:
                api.local('wrong_target', 'test.ping', expr_form='compound')
                {u'return': [{}]}
            """
            if api_return.get('return', [{}]) != [{}]:
                api_return = api_return['return'][0]
                if only_first_match:
                    api_return = next(api_return.iteritems())[1]
                return api_return
            else:
                LOG.info('''Salt api returns empty result: [{}]''')
                return False

        def wait_status(s):
            inspect_res = self.salt_api.local(tgt, 'dockerng.inspect',
                                              self.container_name)
            inspect = simplify_salt_api_return(inspect_res)
            if inspect:
                status = inspect['State']['Status']
                return status.lower() == s.lower()
            return False

        if wait_status('running'):
            helpers.wait(lambda: wait_status('exited'),
                         timeout=timeout,
                         timeout_msg=('Tempest run didnt finished '
                                      'in {}'.format(timeout)))

            inspect_res = self.salt_api.local(tgt, 'dockerng.inspect',
                                              self.container_name)
            inspect = simplify_salt_api_return(inspect_res)

            logs_res = self.salt_api.local(tgt, 'dockerng.logs',
                                           self.container_name)
            logs = simplify_salt_api_return(logs_res)
            rm_res = self.salt_api.local(tgt, 'dockerng.rm',
                                         self.container_name)
            LOG.info("Tempest container was removed: {}".format(
                json.dumps(rm_res, indent=4)))
        else:
            inspect_res = self.salt_api.local(tgt, 'dockerng.inspect',
                                              self.container_name)
            inspect = simplify_salt_api_return(inspect_res)
            if inspect:
                status = inspect['State']['Status']
                LOG.info("Container is not in RUNNING state. "
                         "Current container status is {}".format(status))
                logs_res = self.salt_api.local(tgt,
                                               'dockerng.logs',
                                               self.container_name)
                logs = simplify_salt_api_return(logs_res)
            else:
                LOG.info("dockerng returns unexpected"
                         " result: {}".format(inspect_res))
                logs = None
                inspect = None

        return {'inspect': inspect,
                'logs': logs}

    def prepare_and_run_tempest(self, username='root'):
        """
        Run tempest tests
        """
        tempest_timeout = settings.TEMPEST_TIMEOUT
        self.prepare()
        test_res = self.run_tempest(tempest_timeout)
        self.fetch_arficats(username=username)
        self.save_runtime_logs(**test_res)
