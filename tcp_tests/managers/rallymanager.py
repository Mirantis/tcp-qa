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
import datetime
import json

from devops import error
from functools32 import lru_cache

from tcp_tests import logger
from tcp_tests import settings


LOG = logger.logger


class RallyManager(object):
    """docstring for RallyManager"""

    image_name = (
        'docker-prod-virtual.docker.mirantis.net/'
        'mirantis/oscore/rally-tempest')
    image_version = 'latest'
    tempest_tag = "16.0.0"
    designate_tag = "0.2.0"

    def __init__(self, underlay, rally_node='gtw01.'):
        super(RallyManager, self).__init__()
        self._underlay = underlay
        LOG.info("Rally node is {}".format(rally_node))
        self._node_name = self.get_target_node(target=rally_node)

    @property
    @lru_cache(maxsize=None)
    def image_id(self):
        LOG.info("Getting image id")
        cmd = ("docker images | grep {0}| grep {1}| awk '{{print $3}}'"
               .format(self.image_name, self.image_version))
        res = self._underlay.check_call(cmd, node_name=self._node_name)
        image_id = res['stdout'][0].strip()
        LOG.info("Image ID is {}".format(image_id))
        return image_id

    @property
    @lru_cache(maxsize=None)
    def docker_id(self):
        cmd = ("docker ps | grep {image_id} | "
               "awk '{{print $1}}'| head -1").format(
                   image_id=self.image_id)
        LOG.info("Getting container id")
        res = self._underlay.check_call(cmd, node_name=self._node_name)
        docker_id = res['stdout'][0].strip()
        LOG.info("Container ID is {}".format(docker_id))
        return docker_id

    # Move method to underlay
    def get_target_node(self, target='gtw01.'):
        LOG.info("underlay.node_names: {}".format(self._underlay.node_names()))
        return [node_name for node_name
                in self._underlay.node_names()
                if node_name.startswith(target)][0]

    def _docker_exec(self, cmd, timeout=None, verbose=False):
        docker_cmd = ('docker exec -i {docker_id} bash -c "{cmd}"'
                      .format(cmd=cmd, docker_id=self.docker_id))
        LOG.info("Executing: {docker_cmd}".format(docker_cmd=docker_cmd))
        return self._underlay.check_call(docker_cmd, node_name=self._node_name,
                                         verbose=verbose, timeout=timeout)

    def _run(self):
        """Start the rally container in the background"""
        with self._underlay.remote(node_name=self._node_name) as remote:
            cmd = ("docker run --net host -v /root/rally:/home/rally/.rally "
                   "-v /etc/ssl/certs/:/etc/ssl/certs/ "
                   "-tid -u root --entrypoint /bin/bash {image_id}"
                   .format(image_id=self.image_id))
            LOG.info("Run Rally container")
            remote.check_call(cmd)

    def run_container(self, version=None):
        """Install docker, configure and run rally container"""
        version = version or self.image_version
        image = self.image_name
        LOG.info("Pull {image}:{version}".format(image=image,
                                                 version=version))
        cmd = ("apt-get -y install docker.io &&"
               " docker pull {image}:{version}".format(image=image,
                                                       version=version))
        self._underlay.check_call(cmd, node_name=self._node_name)

        LOG.info("Create rally workdir")
        cmd = 'mkdir -p /root/rally; chown 65500 /root/rally'
        self._underlay.check_call(cmd, node_name=self._node_name)

        LOG.info("Copy keystonercv3")
        cmd = "cp /root/keystonercv3 /root/rally/keystonercv3"
        self._underlay.check_call(cmd, node_name=self._node_name)
        self._run()

        LOG.info("Create rally deployment")
        self._docker_exec("rally-manage db recreate")
        self._docker_exec("source /home/rally/.rally/keystonercv3;"
                          "rally deployment create --fromenv --name=Abathur")
        self._docker_exec("rally deployment list")

    def prepare_rally_task(self, target_node='ctl01.'):
        """Prepare cirros image and private network for rally task"""
        ctl_node_name = self._underlay.get_target_node_names(
            target=target_node)[0]
        cmds = [
            ". keystonercv3 ; openstack flavor create --public m1.tiny",
            ("wget http://download.cirros-cloud.net/0.3.4/"
             "cirros-0.3.4-i386-disk.img"),
            (". /root/keystonercv3; glance --timeout 120 image-create "
             "--name cirros-disk --visibility public --disk-format qcow2 "
             "--container-format bare --progress "
             "< /root/cirros-0.3.4-i386-disk.img"),
            ". /root/keystonercv3; neutron net-create net04",
        ]

        for cmd in cmds:
            self._underlay.check_call(cmd, node_name=ctl_node_name)

    def prepare_tempest_task(self):
        """Configure rally.conf for tempest tests"""
        pass
#        LOG.info("Modify rally.conf")
#        cmd = ("sed -i 's|#swift_operator_role = Member|"
#               "swift_operator_role=SwiftOperator|g' "
#               "/etc/rally/rally.conf")
#        self._docker_exec(cmd)

    def create_rally_task(self, task_path, task_content):
        """Create a file with rally task definition

        :param task_path: path to JSON or YAML file on target node
        :task_content: string with json or yaml content to store in file
        """
        cmd = ("mkdir -p $(dirname {task_path}) && "
               "cat > {task_path} << EOF\n{task_content}\nEOF").format(
            task_path=task_path, task_content=task_content)
        self._underlay.check_call(cmd, node_name=self._node_name)

    def run_task(self, task='', timeout=None, raise_on_timeout=True,
                 verbose=False):
        """Run rally task

        :param taks: path to json or yaml file with the task definition
        :param raise_on_timeout: bool, ignore TimeoutError if False
        :param verbose: show rally output to console if True
        """
        try:
            res = self._docker_exec(
                "rally task start {task}".format(task=task),
                timeout=timeout,
                verbose=verbose)
        except error.TimeoutError:
            if raise_on_timeout:
                raise
            else:
                res = None
                pass
        return res

    # Updated to replace the OpenStackManager method run_tempest
    def run_tempest(self, conf_name='/var/lib/lvm_mcp.conf',
                    pattern='set=smoke', concurrency=0, timeout=None,
                    report_prefix='', report_types=None,
                    designate_plugin=True):
        """Run tempest tests

        :param conf_name: tempest config placed in the rally container
        :param pattern: tempest testcase name or one of existing 'set=...'
        :param concurrency: how many threads to use in parallel. 0 means
                            to take the amount of the cores on the node
                            <self._node_name>.
        :param timeout: stop tempest tests after specified timeout.
        :param designate_plugin: enabled by default plugin for designate
        :param report_prefix: str, prefix for report filenames. Usually the
                              output of the fixture 'func_name'
        :param report_types: list of the report types that need to download
                             from the environment: ['html', 'xml', 'json'].
                             None by default.
        """
        report_types = report_types or []
        if not designate_plugin:
            cmd = (
                "cat > /root/rally/install_tempest.sh << EOF\n"
                "rally verify create-verifier"
                "  --type tempest "
                "  --name tempest-verifier"
                "  --source /var/lib/tempest"
                "  --version {tempest_tag}"
                "  --system-wide\n"
                "rally verify configure-verifier --extend {tempest_conf}\n"
                "rally verify configure-verifier --show\n"
                "EOF".format(tempest_tag=self.tempest_tag,
                             tempest_conf=conf_name))
        else:
            cmd = (
                "cat > /root/rally/install_tempest.sh << EOF\n"
                "rally verify create-verifier"
                "  --type tempest "
                "  --name tempest-verifier"
                "  --source /var/lib/tempest"
                "  --version {tempest_tag}"
                "  --system-wide\n"
                "rally verify add-verifier-ext"
                "  --source /var/lib/designate-tempest-plugin"
                "  --version {designate_tag}\n"
                "rally verify configure-verifier --extend {tempest_conf}\n"
                "rally verify configure-verifier --show\n"
                "EOF".format(tempest_tag=self.tempest_tag,
                             designate_tag=self.designate_tag,
                             tempest_conf=conf_name))
        with self._underlay.remote(node_name=self._node_name) as remote:
            LOG.info("Create install_tempest.sh")
            remote.check_call(cmd)
            remote.check_call("chmod +x /root/rally/install_tempest.sh")

        LOG.info("Run tempest inside Rally container")
        self._docker_exec("/home/rally/.rally/install_tempest.sh")
        self._docker_exec(
            ("source /home/rally/.rally/keystonercv3 && "
             "rally verify start --skip-list /var/lib/mcp_skip.list "
             "  --concurrency {concurrency} --pattern {pattern}"
             .format(concurrency=concurrency, pattern=pattern)),
            timeout=timeout, verbose=True)
        if report_prefix:
            report_filename = '{0}_report_{1}'.format(
                report_prefix,
                datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        else:
            report_filename = 'report_{1}'.format(
                datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        docker_file_prefix = '/home/rally/.rally/' + report_filename

        # Create reports
        if 'xml' in report_types:
            self._docker_exec(
                "rally verify report --type junit-xml --to {0}.xml"
                .format(docker_file_prefix))
        if 'html' in report_types:
            self._docker_exec(
                "rally verify report --type html --to {0}.html"
                .format(docker_file_prefix))
        # Always create report in JSON to return results into test case
        # However, it won't be downloaded until ('json' in report_prefix)
        self._docker_exec("rally verify report --type json --to {0}.json"
                          .format(docker_file_prefix))

        # Download reports to the settings.LOGS_DIR
        file_src_prefix = '/root/rally/{0}'.format(report_filename)
        file_dst_prefix = '{0}/{1}'.format(settings.LOGS_DIR, report_filename)
        with self._underlay.remote(node_name=self._node_name) as remote:
            for suffix in report_types:
                remote.download(file_src_prefix + '.' + suffix,
                                file_dst_prefix + '.' + suffix)
            res = json.load(remote.open(file_src_prefix + '.json'))

        # Get latest verification ID to find the lates testcases in the report
        vtime = {vdata['finished_at']: vid
                 for vid, vdata in res['verifications'].items()}
        vlatest_id = vtime[max(vtime.keys())]

        # Each status has the dict with pairs:
        #   <status>: {
        #       <case_name>: <case_details>,
        #    }
        formatted_tc = {
            'success': {},
            'fail': {},
            'xfail': {},
            'skip': {}
        }

        for tname, tdata in res['tests'].items():
            status = tdata['by_verification'][vlatest_id]['status']
            details = tdata['by_verification'][vlatest_id].get('details', '')
            if status not in formatted_tc:
                # Fail if tempest return a new status that may be
                # necessary to take into account in test cases
                raise Exception("Unknown testcase {0} status: {1} "
                                .format(tname, status))
            formatted_tc[status][tdata['name']] = details
        LOG.debug("Formatted testcases: {0}".format(formatted_tc))
        return formatted_tc
