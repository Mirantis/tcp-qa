from __future__ import print_function
import time

import jenkins
import requests

from devops.helpers import helpers


class JenkinsClient(object):

    def __init__(self, host=None, username=None, password=None):
        host = host or 'http://172.16.44.33:8081'
        username = username or 'admin'
        password = password or 'r00tme'
        self.__client = jenkins.Jenkins(
            host,
            username=username,
            password=password)

    def jobs(self):
        return self.__client.get_jobs()

    def find_jobs(self, name):
        return filter(lambda x: name in x['fullname'], self.jobs())

    def job_info(self, name):
        return self.__client.get_job_info(name)

    def list_builds(self, name):
        return self.job_info(name).get('builds')

    def build_info(self, name, build_id):
        return self.__client.get_build_info(name, build_id)

    def job_params(self, name):
        job = self.job_info(name)
        job_params = next(
            p for p in job['property'] if
            'hudson.model.ParametersDefinitionProperty' == p['_class'])
        job_params = job_params['parameterDefinitions']
        return job_params

    def make_defults_params(self, name):
        job_params = self.job_params(name)
        def_params = dict(
            [(j['name'], j['defaultParameterValue']['value'])
             for j in job_params])
        return def_params

    def run_build(self, name, params=None, timeout=600, verbose=False):
        params = params or self.make_defults_params(name)
        num = self.__client.build_job(name, params)

        def is_blocked():
            queued = self.__client.get_queue_item(num)
            status = not queued['blocked']
            if not status and verbose:
                print("pending the job [{}] : {}".format(name, queued['why']))
            return status

        helpers.wait(
            is_blocked,
            timeout=timeout,
            interval=30,
            timeout_msg='Timeout waiting to run the job [{}]'.format(name))

        build_id = self.__client.get_queue_item(num)['executable']['number']
        return name, build_id

    def wait_end_of_build(self, name, build_id, timeout=600,
                          verbose=False):
        start = [0]

        def building():
            status = not self.build_info(name, build_id)['building']
            if verbose:
                res = self.get_progressive_build_output(name,
                                                        build_id,
                                                        start=start[0])
                if 'X-Text-Size' in res.headers:
                    text_size = int(res.headers['X-Text-Size'])
                    if start[0] < text_size:
                        print(res.content, end='')
                        start[0] = text_size
            return status

        helpers.wait(
            building,
            timeout=timeout,
            timeout_msg='Timeout waiting, job {0} are not finished "{1}" build'
                        ' still'.format(name, build_id))

    def get_build_output(self, name, build_id):
        return self.__client.get_build_console_output(name, build_id)

    def get_progressive_build_output(self, name, build_id, start=0,
                                     raise_on_err=False):
        '''Get build console text.

        :param name: Job name, ``str``
        :param name: Build id, ``int``
        :param name: Start offset, ``int``
        :returns: requests object with headers and console output,  ``obj``
        '''
        folder_url, short_name = self.__client._get_job_folder(name)

        PROGRESSIVE_CONSOLE_OUTPUT = (
            '%(folder_url)sjob/%(short_name)s/%(build_id)d/'
            'logText/progressiveHtml?start=%(start)d')
        url = self.__client._build_url(PROGRESSIVE_CONSOLE_OUTPUT, locals())
        return(requests.get(url))
