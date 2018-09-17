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
import time

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
    master_tgt = "{}*".format(master_host)
    class_name = "runtest"
    run_cmd = '/bin/bash -c "run-tempest"'

    def __init__(self, config, underlay, salt_api, cluster_name,
                 domain_name, tempest_threads,
                 tempest_pattern=settings.TEMPEST_PATTERN,
                 run_cmd=None, target='gtw01'):
        self.__config = config
        self.underlay = underlay
        self.__salt_api = salt_api
        self.cluster_name = cluster_name
        self.domain_name = domain_name
        self.tempest_threads = tempest_threads
        self.tempest_pattern = tempest_pattern
        self.run_cmd = run_cmd or self.run_cmd
        targets = [node_name for node_name
                   in self.underlay.node_names() if
                   target in node_name]
        assert len(targets) == 1, (
            'For target pattern {0} exactly one target must be selected, '
            'actually got: {1}'.format(target, targets))
        self.target_name = targets[0]

    @property
    def salt_api(self):
        return self.__salt_api

    @property
    def runtest_pillar(self):
        public_net = self.__config.underlay.dhcp_ranges[
            settings.EXTERNAL_ADDRESS_POOL_NAME]
        public_gateway = public_net["gateway"].encode("ascii")
        public_cidr = public_net["cidr"].encode("ascii")
        public_allocation_start = public_net["start"].encode("ascii")
        public_allocation_end = public_net["end"].encode("ascii")

        return {
            'classes': ['service.runtest.tempest',
                        'service.runtest.tempest.public_net',
                        'service.runtest.tempest.services.manila.glance'],
            'parameters': {
                '_param': {
                    'runtest_tempest_cfg_dir': TEMPEST_CFG_DIR,
                    'runtest_tempest_cfg_name': 'tempest.conf',
                    'runtest_tempest_public_net': 'public',
                    'openstack_public_neutron_subnet_gateway': public_gateway,
                    'openstack_public_neutron_subnet_cidr': public_cidr,
                    'openstack_public_neutron_subnet_allocation_start':
                        public_allocation_start,
                    'openstack_public_neutron_subnet_allocation_end':
                        public_allocation_end,
                    'tempest_test_target': self.target_name.encode("ascii"),
                },
                'neutron': {
                    'client': {
                        'enabled': True
                    }
                },
                'runtest': {
                    'enabled': True,
                    'keystonerc_node': 'ctl01*',
                    'tempest': {
                        'enabled': True,
                        'cfg_dir': '${_param:runtest_tempest_cfg_dir}',
                        'cfg_name': '${_param:runtest_tempest_cfg_name}',
                        'DEFAULT': {
                            'log_file': 'tempest.log'
                        },
                        'compute': {
                            'build_timeout': 600,
                            'max_microversion': 2.53,
                            'min_compute_nodes': 2,
                            'min_microversion': 2.1,
                            'volume_device_name': 'vdc'
                        },
                        'convert_to_uuid': {
                            'network': {
                                'public_network_id':
                                '${_param:runtest_tempest_public_net}'
                            }
                        },
                        'dns_feature_enabled': {
                            'api_admin': False,
                            'api_v1': False,
                            'api_v2': True,
                            'api_v2_quotas': True,
                            'api_v2_root_recordsets': True,
                            'bug_1573141_fixed': True
                        },
                        'heat_plugin': {
                            'floating_network_name':
                            '${_param:runtest_tempest_public_net}'
                        },
                        'network': {
                            'floating_network_name':
                            '${_param:runtest_tempest_public_net}'
                        },
                        'share': {
                            'capability_snapshot_support': True,
                            'run_driver_assisted_migration_tests': False,
                            'run_manage_unmanage_snapshot_tests': False,
                            'run_manage_unmanage_tests': False,
                            'run_migration_with_preserve_snapshots_tests':
                                False,
                            'run_quota_tests': True,
                            'run_replication_tests': False,
                            'run_snapshot_tests': True,
                        }}}}}

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

    def store_runtest_model(self, runtest_pillar=None):
        master_name = next(node_name for node_name
                           in self.underlay.node_names() if
                           self.master_host in node_name)
        with self.underlay.yaml_editor(
                file_path="/srv/salt/reclass/classes/cluster/"
                          "{cluster_name}/infra/"
                          "{class_name}.yml".format(
                              cluster_name=self.cluster_name,
                              class_name=self.class_name),
                node_name=master_name) as editor:
            editor.content = runtest_pillar or self.runtest_pillar
        with self.underlay.yaml_editor(
                file_path="/srv/salt/reclass/nodes/_generated/"
                          "cfg01.{domain_name}.yml".format(
                              domain_name=self.domain_name),
                node_name=master_name) as editor:
            editor.content['classes'].append(
                'cluster.{cluster_name}.infra.{class_name}'.format(
                    cluster_name=self.cluster_name,
                    class_name=self.class_name))


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

    def prepare(self, dpdk=None):
        self.store_runtest_model()

        salt_cmd = ("salt --hard-crash --state-output=mixed"
                    " --state-verbose=False ")
        salt_call_cmd = ("salt-call --hard-crash --state-output=mixed"
                         " --state-verbose=False ")
        commands = [
            {
                'description': "Sync salt objects for runtest model",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_cmd + "'*' saltutil.refresh_pillar && " +
                        salt_cmd + "'*' saltutil.sync_all")},
            {
                'description': ("Install docker.io package and "
                                "enable packets forwarding"),
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " pkg.install docker.io && " +
                        " iptables --policy FORWARD ACCEPT"},
            {
                'description': "Install PyPI docker package",
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " pip.install setuptools && " +
                        salt_call_cmd + " pip.install docker"},
            {
                'description': "Run salt.minion state for runtest formula",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls salt.minion && "
                        " sleep 20"},
            {
                'description': "Create networks for Tempest tests",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls neutron.client && "
                        " sleep 20"},
            {
                'description': "Create flavors for Tempest tests",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls nova.client && "
                        " sleep 20"},
            {
                'description': "Create cirros image for Tempest",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls glance.client && "
                        " sleep 20"},
            {
                'description': "Generate config for Tempest",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls runtest && "
                        " sleep 20"},
        ]

        if dpdk:
            commands.append({
                'description': "Configure flavor for DPDK",
                'node_name': 'cfg01*',
                'cmd': ("set -ex;" +
                        salt_call_cmd + " cmd.run "
                        " '. /root/keystonercv3;"
                        "  openstack flavor set m1.tiny_test"
                        "  --property hw:mem_page_size=small'"
                        " && sleep 20"},
            )

        salt_api.execute_commands(commands=commands,
                                  label="Prepare for Tempest")

    def run_tempest(self, timeout=600):
        tgt = self.target_name
        params = {
            "name": self.container_name,
            "image": "{}:{}".format(self.image_name, self.image_version),
            "environment": {
                "ARGS": "-r {tempest_pattern} -w "
                        "{tempest_threads} ".format(
                            tempest_pattern=self.tempest_pattern,
                            tempest_threads=self.tempest_threads)  # noqa
            },
            "binds": [
                "{cfg_dir}/tempest.conf:/etc/tempest/tempest.conf".format(cfg_dir=TEMPEST_CFG_DIR),  # noqa
                "/tmp/:/tmp/",
                "{cfg_dir}:/root/tempest".format(cfg_dir=TEMPEST_CFG_DIR),
                "/etc/ssl/certs/:/etc/ssl/certs/"
            ],
            "auto_remove": False,
            "cmd": self.run_cmd
        }

        res = self.salt_api.local(tgt, 'docker.pull', "{}:{}".format(
            self.image_name, self.image_version))
        LOG.info("Tempest image has beed pulled- \n{}".format(
            json.dumps(res, indent=4)))

        res = self.salt_api.local(tgt, 'docker.create', kwargs=params)
        LOG.info("Tempest container has been created - \n{}".format(
            json.dumps(res, indent=4)))

        res = self.salt_api.local(tgt, 'docker.start', self.container_name)
        LOG.info("Tempest container has been started - \n{}".format(
            json.dumps(res, indent=4)))

        def wait_status(s):
            inspect_res = self.salt_api.local(tgt,
                                              'docker.inspect',
                                              self.container_name)
            if 'return' in inspect_res:
                inspect = inspect_res['return']
                inspect = inspect[0]
                inspect = next(inspect.iteritems())[1]
                status = inspect['State']['Status']

                return status.lower() == s.lower()

            return False

        helpers.wait(lambda: wait_status('exited'),
                     timeout=timeout,
                     timeout_msg=('Tempest run didnt finished '
                                  'in {}'.format(timeout)))

        inspect_res = self.salt_api.local(tgt,
                                          'docker.inspect',
                                          self.container_name)
        inspect = inspect_res['return'][0]
        inspect = next(inspect.iteritems())[1]
        if inspect['State']['ExitCode'] != 0:
            LOG.error("Tempest running failed")
        LOG.info("Tempest tests have been finished - \n{}".format(
            json.dumps(res, indent=4)))

        logs_res = self.salt_api.local(tgt,
                                       'docker.logs',
                                       self.container_name)
        logs = logs_res['return'][0]
        logs = next(logs.iteritems())[1]
        LOG.info("Tempest result - \n{}".format(
            logs.encode('ascii', 'ignore')))

        res = self.salt_api.local(tgt, 'docker.rm', self.container_name)
        LOG.info("Tempest container was removed".format(
            json.dumps(res, indent=4)))

        return {'inspect': inspect,
                'logs': logs}

    def prepare_and_run_tempest(self, username='root', dpdk=None):
        """
        Run tempest tests
        """
        tempest_timeout = settings.TEMPEST_TIMEOUT
        self.prepare(dpdk=dpdk)
        test_res = self.run_tempest(tempest_timeout)
        self.fetch_arficats(username=username)
        self.save_runtime_logs(**test_res)
