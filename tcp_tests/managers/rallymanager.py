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

from junit_xml import TestSuite, TestCase

from tcp_tests import logger
from tcp_tests import settings


LOG = logger.logger


class RallyManager(object):
    """docstring for RallyManager"""

    image_name = 'rallyforge/rally'
    image_version = '0.9.1'

    def __init__(self, underlay, admin_host):
        super(RallyManager, self).__init__()
        self._admin_host = admin_host
        self._underlay = underlay

    def prepare(self):
        content = """
sed -i 's|#swift_operator_role = Member|swift_operator_role=SwiftOperator|g' /etc/rally/rally.conf  # noqa
source /home/rally/openrc
rally-manage db recreate
rally deployment create --fromenv --name=tempest
rally verify create-verifier --type tempest --name tempest-verifier
rally verify configure-verifier
rally verify configure-verifier --show
"""
        cmd = "cat > {path} << EOF\n{content}\nEOF".format(
            path='/root/rally/install_tempest.sh', content=content)
        cmd1 = "chmod +x /root/rally/install_tempest.sh"
        cmd2 = "scp ctl01:/root/keystonercv3 /root/rally/openrc"

        with self._underlay.remote(host=self._admin_host) as remote:
            LOG.info("Create rally workdir")
            remote.check_call('mkdir -p /root/rally')
            LOG.info("Create install_tempest.sh")
            remote.check_call(cmd)
            LOG.info("Chmod +x install_tempest.sh")
            remote.check_call(cmd1)
            LOG.info("Copy openstackrc")
            remote.check_call(cmd2)

    def pull_image(self, version=None):
        version = version or self.image_version
        image = self.image_name
        cmd = ("apt-get -y install docker.io &&"
               " docker pull {image}:{version}".format(image=image,
                                                       version=version))
        with self._underlay.remote(host=self._admin_host) as remote:
            LOG.info("Pull {image}:{version}".format(image=image,
                                                     version=version))
            remote.check_call(cmd)

        with self._underlay.remote(host=self._admin_host) as remote:
            LOG.info("Getting image id")
            cmd = "docker images | grep {0}| awk '{{print $3}}'".format(
                self.image_version)
            res = remote.check_call(cmd)
            self.image_id = res['stdout'][0].strip()
            LOG.info("Image ID is {}".format(self.image_id))

    def run(self):
        with self._underlay.remote(host=self._admin_host) as remote:
            cmd = ("docker run --net host -v /root/rally:/home/rally "
                   "-tid -u root {image_id}".format(image_id=self.image_id))
            LOG.info("Run Rally container")
            remote.check_call(cmd)

            cmd = ("docker ps | grep {image_id} | "
                   "awk '{{print $1}}'| head -1").format(
                       image_id=self.image_id)
            LOG.info("Getting container id")
            res = remote.check_call(cmd)
            self.docker_id = res['stdout'][0].strip()
            LOG.info("Container ID is {}".format(self.docker_id))

    def run_tempest(self, test=''):
        docker_exec = ('docker exec -i {docker_id} bash -c "{cmd}"')
        commands = [
            docker_exec.format(cmd="./install_tempest.sh",
                               docker_id=self.docker_id),
            docker_exec.format(
                cmd="source /home/rally/openrc && "
                    "rally verify start {test}".format(test=test),
                docker_id=self.docker_id),
            docker_exec.format(
                cmd="rally verify report --type json --to result.json",
                docker_id=self.docker_id),
            docker_exec.format(
                cmd="rally verify report --type html --to result.html",
                docker_id=self.docker_id),
        ]
        with self._underlay.remote(host=self._admin_host) as remote:
            LOG.info("Run tempest inside Rally container")
            for cmd in commands:
                remote.check_call(cmd, verbose=True)

    def get_results(self, store=True, store_file='tempest.xml'):
        LOG.info('Storing tests results...')
        res_file_name = 'result.json'
        file_prefix = 'results_' + datetime.datetime.now().strftime(
            '%Y%m%d_%H%M%S') + '_'
        file_dst = '{0}/{1}{2}'.format(
            settings.LOGS_DIR, file_prefix, res_file_name)
        with self._underlay.remote(host=self._admin_host) as remote:
            remote.download(
                '/root/rally/{0}'.format(res_file_name),
                file_dst)
            res = json.load(remote.open('/root/rally/result.json'))
        if not store:
            return res

        formatted_tc = []
        failed_cases = [res['test_cases'][case]
                        for case in res['test_cases']
                        if res['test_cases'][case]['status']
                        in 'fail']
        for case in failed_cases:
            if case:
                tc = TestCase(case['name'])
                tc.add_failure_info(case['traceback'])
                formatted_tc.append(tc)

        skipped_cases = [res['test_cases'][case]
                         for case in res['test_cases']
                         if res['test_cases'][case]['status'] in 'skip']
        for case in skipped_cases:
            if case:
                tc = TestCase(case['name'])
                tc.add_skipped_info(case['reason'])
                formatted_tc.append(tc)

        error_cases = [res['test_cases'][case] for case in res['test_cases']
                       if res['test_cases'][case]['status'] in 'error']

        for case in error_cases:
            if case:
                tc = TestCase(case['name'])
                tc.add_error_info(case['traceback'])
                formatted_tc.append(tc)

        success = [res['test_cases'][case] for case in res['test_cases']
                   if res['test_cases'][case]['status'] in 'success']
        for case in success:
            if case:
                tc = TestCase(case['name'])
                formatted_tc.append(tc)

        ts = TestSuite("tempest", formatted_tc)
        with open(store_file, 'w') as f:
            ts.to_file(f, [ts], prettyprint=False)

        return res
