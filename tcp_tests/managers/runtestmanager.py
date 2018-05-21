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

import os
import json

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests import settings


LOG = logger.logger

TEMPEST_CFG_DIR = '/tmp/test'

CONFIG = {
    'classes': ['service.runtest.tempest'],
    'parameters': {
        '_param': {
            'runtest_tempest_cfg_dir': TEMPEST_CFG_DIR,
            'runtest_tempest_cfg_name': 'tempest.conf',
            'runtest_tempest_public_net': 'net04_ext',
            'tempest_test_target': 'gtw01*'
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
                    'max_microversion': 2.5299999999999998,
                    'min_compute_nodes': 2,
                    'min_microversion': 2.1000000000000001,
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
                    'backend_names': 'lvm',
                    'capability_create_share_from_snapshot_support': True,
                    'capability_snapshot_support': True,
                    'default_share_type_name': 'default',
                    'enable_ip_rules_for_protocols': 'nfs',
                    'enable_user_rules_for_protocols': 'cifs',
                    'max_api_microversion': 2.3999999999999999,
                    'min_api_microversion': 2.0,
                    'run_driver_assisted_migration_tests': False,
                    'run_host_assisted_migration_tests': True,
                    'run_manage_unmanage_snapshot_tests': False,
                    'run_manage_unmanage_tests': False,
                    'run_migration_with_preserve_snapshots_tests': False,
                    'run_mount_snapshot_tests': True,
                    'run_quota_tests': True,
                    'run_replication_tests': False,
                    'run_revert_to_snapshot_tests': True,
                    'run_share_group_tests': False,
                    'run_shrink_tests': False,
                    'run_snapshot_tests': True,
                    'share_creation_retry_number': 2,
                    'suppress_errors_in_cleanup': True
                }}}}}


class RuntestManager(object):
    """Helper manager for execution tempest via runtest-formula"""

    image_name = (
        'docker-prod-virtual.docker.mirantis.net/mirantis/cicd/ci-tempest')
    image_version = 'latest'
    container_name = 'run-tempest-ci_2'
    master_host = "cfg01"
    master_tgt = "{}*".format(master_host)
    class_name = "runtest2"
    run_cmd = '/bin/bash -c "run-tempest"'

    def __init__(self, underlay, salt_api, cluster_name, domain_name,
                 tempest_threads, tempest_exclude_test_args, tempest_pattern,
                 run_cmd=None, target='gtw01'):
        self.underlay = underlay
        self.__salt_api = salt_api
        self.target = target
        self.cluster_name = cluster_name
        self.domain_name = domain_name
        self.tempest_threads = tempest_threads
        self.tempest_exclude_test_args = tempest_exclude_test_args
        self.tempest_pattern = tempest_pattern
        self.run_cmd = run_cmd or self.run_cmd

    @property
    def salt_api(self):
        return self.__salt_api

    def install_python_lib(self):
        return self.salt_api.local(
            "{}*".format(self.target),
            'pip.install', 'docker'), None

    def install_formula(self):
        return self.salt_api.local(
            self.master_tgt,
            'pkg.install', 'salt-formula-runtest'), None

    def create_networks(self):
        return self.salt_api.enforce_state(self.master_tgt, 'neutron.client')

    def create_flavors(self):
        return self.salt_api.enforce_state(self.master_tgt, 'nova.client')

    def create_cirros(self):
        return self.salt_api.enforce_state(self.master_tgt, 'glance.client')

    def generate_config(self):
        return self.salt_api.enforce_state(self.master_tgt, 'runtest')

    def fetch_arficats(self, username=None):
        target_name = next(node_name for node_name
                           in self.underlay.node_names() if
                           self.target in node_name)
        with self.underlay.remote(node_name=target_name, username=None) as tgt:
            tgt.download(
                destination="{cfg_dir}/report_*.xml".format(cfg_dir=TEMPEST_CFG_DIR),  # noqa
                target="{}".format(os.environ.get("PWD")))

    def store_runtest_model(self):
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
            editor.content = CONFIG

        with self.underlay.yaml_editor(
                file_path="/srv/salt/reclass/nodes/_generated/"
                          "cfg01.{domain_name}.yml".format(
                              domain_name=self.domain_name),
                node_name=master_name) as editor:
            editor.content['classes'].append(
                'cluster.{cluster_name}.infra.{class_name}'.format(
                    cluster_name=self.cluster_name,
                    class_name=self.class_name))

        self.salt_api.local('*', 'saltutil.refresh_pillar')
        self.salt_api.local('*', 'saltutil.sync_all')

    def save_runtime_logs(self, logs=None, inspect=None):
        if logs:
            with open("{path}/{target}_tempest_run.log".format(
                    path=settings.LOGS_DIR, target=self.target), 'w') as f:
                LOG.info("Save tempest console log")
                container_log = logs
                f.write(container_log)

        if inspect:
            with open("{path}/{target}_tempest_container_info.json".format(
                    path=settings.LOGS_DIR, target=self.target), 'w') as f:
                LOG.info("Save tempest containes inspect data")

                container_inspect = json.dumps(inspect,
                                               indent=4, sort_keys=True)
                f.write(container_inspect)

    def prepare(self):
        self.store_runtest_model()
        res = self.install_formula()
        LOG.info(res)
        res = self.install_python_lib()
        LOG.info(res)
        res = self.create_networks()
        LOG.info(res)
        res = self.create_flavors()
        LOG.info(res)
        res = self.create_cirros()
        LOG.info(res)
        res = self.generate_config()
        LOG.info(res)

    def run_tempest(self):
        tgt = "{}*".format(self.target)
        params = {
            "name": self.container_name,
            "image": self.image_name,
            "environment": {
                "ARGS": "-r {tempest_pattern} -w "
                        "{tempest_threads} "
                        "{tempest_exclude_test_args}".format(
                            tempest_pattern=self.tempest_pattern,
                            tempest_threads=self.tempest_threads,
                            tempest_exclude_test_args=self.tempest_exclude_test_args)  # noqa
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
        res = self.salt_api.local(tgt, 'dockerng.pull', self.image_name)
        LOG.info(res)
        res = self.salt_api.local(tgt, 'dockerng.create', kwargs=params)
        LOG.info(res)
        res = self.salt_api.local(tgt, 'dockerng.start', self.container_name)
        LOG.info(res)

        def wait_status(s):
            inspect_res = self.salt_api.local(tgt,
                                              'dockerng.inspect',
                                              self.container_name)
            if 'return' in inspect_res:
                inspect = inspect_res['return']
                inspect = inspect[0]
                inspect = next(inspect.iteritems())[1]
                status = inspect['State']['Status']

                return status.lower() == s.lower()

            return False

        timeout = 60
        helpers.wait(lambda: wait_status('exited'),
                     timeout=timeout,
                     timeout_msg=('Tempest run didnt finished '
                                  'in {}'.format(timeout)))

        inspect_res = self.salt_api.local(tgt,
                                          'dockerng.inspect',
                                          self.container_name)
        inspect = inspect_res['return'][0]
        inspect = next(inspect.iteritems())[1]
        if inspect['State']['ExitCode'] != 0:
            LOG.error("Tempest running failed")

        logs_res = self.salt_api.local(tgt,
                                       'dockerng.logs',
                                       self.container_name)
        logs = logs_res['return'][0]
        logs = next(logs.iteritems())[1]

        res = self.salt_api.local(tgt, 'dockerng.rm', self.container_name)
        LOG.info(res)

        return {'inspect': inspect,
                'logs': logs}
