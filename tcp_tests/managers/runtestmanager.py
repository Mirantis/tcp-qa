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
    control_host = "ctl01"
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
        self.target_name = self.underlay.get_target_node_names(target)[0]
        self.master_name = self.underlay.get_target_node_names(
            self.master_host)[0]
        self.control_name = self.underlay.get_target_node_names(
            self.control_host)[0]

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
                        'put_keystone_rc_enabled': True,
                        'put_local_image_file_enabled': False,
                        'DEFAULT': {
                            'log_file': 'tempest.log'
                        },
                        'compute': {
                            'min_compute_nodes': 2,
                        },
                        'convert_to_uuid': {
                            'network': {
                                'public_network_id':
                                '${_param:runtest_tempest_public_net}'
                            }
                        },
                        'heat_plugin': {
                            'build_timeout': '600'
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
        with self.underlay.yaml_editor(
                file_path="/srv/salt/reclass/classes/cluster/"
                          "{cluster_name}/infra/"
                          "{class_name}.yml".format(
                              cluster_name=self.cluster_name,
                              class_name=self.class_name),
                node_name=self.master_name) as editor:
            editor.content = runtest_pillar or self.runtest_pillar
        with self.underlay.yaml_editor(
                file_path="/srv/salt/reclass/nodes/_generated/"
                          "cfg01.{domain_name}.yml".format(
                              domain_name=self.domain_name),
                node_name=self.master_name) as editor:
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
        cirros_pillar = ("salt-call --out=newline_values_only "
                         "pillar.get "
                         "glance:client:identity:"
                         "admin_identity:image:cirros:location")
        salt_cmd = "salt -l info --hard-crash --state-output=mixed "
        salt_call_cmd = "salt-call -l info --hard-crash --state-output=mixed "
        commands = [
            {
                'description': "Sync salt objects for runtest model",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_cmd + "'*' saltutil.refresh_pillar && " +
                        salt_cmd + "'*' saltutil.sync_all")},
            {
                'description': ("Install docker.io package and "
                                "enable packets forwarding"),
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " pkg.install docker.io && " +
                        " iptables --policy FORWARD ACCEPT")},
            {
                'description': "Install PyPI docker package",
                'node_name': self.target_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " pip.install setuptools && " +
                        salt_call_cmd + " pip.install docker")},
            {
                'description': "Run salt.minion state for runtest formula",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls salt.minion && "
                        " sleep 20")},
            {
                'description': "Enforce keystone state for neutronv2",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls keystone.client")},
            {
                'description': "Create networks for Tempest tests",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls neutron.client")},
            {
                'description': "Create flavors for Tempest tests",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls nova.client")},
            {
                'description': "Upload images for Tempest",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls glance.client")},
            {
                'description': "Generate config for Tempest",
                'node_name': self.master_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " state.sls runtest")},
            {
                'description': "Upload cirros image",
                'node_name': self.master_name,
                'cmd': ("set -ex;"
                        "cirros_url=$({}) && {} '{}' cmd.run "
                        "\"wget $cirros_url -O /tmp/TestCirros-0.3.5.img\""
                        .format(cirros_pillar, salt_cmd, self.target_name))},
        ]

        if dpdk:
            commands.append({
                'description': "Configure flavor for DPDK",
                'node_name': self.control_name,
                'cmd': ("set -ex;" +
                        salt_call_cmd + " cmd.run "
                        " '. /root/keystonercv3;"
                        "  openstack flavor set m1.tiny_test"
                        "  --property hw:mem_page_size=small'")},
            )

        self.__salt_api.execute_commands(commands=commands,
                                         label="Prepare for Tempest")

    def run_tempest(self, timeout=600):
        tgt = self.target_name
        image_nameversion = "{}:{}".format(self.image_name, self.image_version)

        docker_args = (
            " -t "
            " --name {container_name} "
            " -e ARGS=\"-r {tempest_pattern} -w {tempest_threads}\""
            " -v {cfg_dir}/tempest.conf:/etc/tempest/tempest.conf"
            " -v /tmp/:/tmp/"
            " -v {cfg_dir}:/root/tempest"
            " -v /etc/ssl/certs/:/etc/ssl/certs/"
            " -d "
            " {image_nameversion} {run_cmd}"
            .format(
                container_name=self.container_name,
                image_nameversion=image_nameversion,
                tempest_pattern=self.tempest_pattern,
                tempest_threads=self.tempest_threads,
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

        helpers.wait(lambda: wait_status('exited'),
                     timeout=timeout,
                     timeout_msg=('Tempest run didnt finished '
                                  'in {}'.format(timeout)))

        inspect_res = self.salt_api.local(tgt,
                                          'dockerng.inspect',
                                          self.container_name)
        inspect = inspect_res['return'][0]
        inspect = next(inspect.iteritems())[1]
        logs_res = self.salt_api.local(tgt,
                                       'dockerng.logs',
                                       self.container_name)
        logs = logs_res['return'][0]
        logs = next(logs.iteritems())[1]

        res = self.salt_api.local(tgt, 'dockerng.rm', self.container_name)
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
