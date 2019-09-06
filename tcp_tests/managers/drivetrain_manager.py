#    Copyright 2017 Mirantis, Inc.
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
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages
from tcp_tests import logger

LOG = logger.logger


class DrivetrainManager(ExecuteCommandsMixin):
    """docstring for DrivetrainManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt=None):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        super(DrivetrainManager, self).__init__(
            config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install Drivetrain Tools')
        self.__config.drivetrain.drivetrain_installed = True

    def start_job_on_cid_jenkins(self, job_name,
                                 **kwargs):
        """
        Starts job with specific parameters on cluster Jenkins

        Method accept any param:
            job_parameters=None,
            job_output_prefix='',
            start_timeout=1800,
            build_timeout=3600 * 4,
            verbose=False

        :param job_name: string
        :return: string, Result of passed job, "SUCCESS"| "FAILED" | "UNSTABLE"
        """
        jenkins_url, jenkins_user, jenkins_pass = self.get_jenkins_creds(
            tgt='I@docker:client:stack:jenkins and cid01*')

        job_result = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            **kwargs)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        if job_result != 'SUCCESS':
            LOG.warning("{0}\n{1}".format(description, '\n'.join(stages)))
        return job_result

    def start_job_on_cfg_jenkins(self):
        pass

    def get_jenkins_creds(self, tgt):
        """
        Requests Jenkins's login parameters from pillars from desired node

        :return: tuple {jenkins_url, jenkins_user, jenkins_pass}
        """
        jenkins_host = self._salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:host")
        if jenkins_host is None:
            raise Exception(
                "Can't find 'jenkins:client:master' pillar on {tgt} node."
                .format(tgt=tgt))
        jenkins_port = self._salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:port")
        jenkins_protocol = self._salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:proto")
        jenkins_url = '{0}://{1}:{2}'.format(jenkins_protocol,
                                             jenkins_host,
                                             jenkins_port)
        jenkins_user = self._salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:username")
        jenkins_pass = self._salt.get_single_pillar(
            tgt=tgt, pillar="jenkins:client:master:password")
        return jenkins_url, jenkins_user, jenkins_pass
