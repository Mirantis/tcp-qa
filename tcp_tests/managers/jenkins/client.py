from __future__ import print_function
import datetime
import time

import jenkins
import json
import requests

from devops.helpers import helpers

from requests.exceptions import ConnectionError


class JenkinsClient(object):

    def __init__(self, host=None, username='admin', password='r00tme'):
        host = host or 'http://172.16.44.33:8081'
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
        time.sleep(2)  # wait while job is started

        def is_build_queued():
            try:
                item = self.__client.get_queue_item(num)
                ts = item['inQueueSince'] / 1000
                since_time = datetime.datetime.fromtimestamp(ts)
                print("Build in the queue since {}".format(since_time))
                return True
            except jenkins.JenkinsException:
                if verbose:
                    print("Build have not been queued {} yet".format(num))

        helpers.wait(
            is_build_queued,
            timeout=timeout,
            interval=30,
            timeout_msg='Timeout waiting to queue the build '
                        'for {} job'.format(name))

        def is_blocked():
            queued = self.__client.get_queue_item(num)
            status = not queued['blocked']
            if not status and verbose:
                print("pending the job [{}] : {}".format(name, queued['why']))
            return (status and
                    'executable' in (queued or {}) and
                    'number' in (queued['executable'] or {}))

        helpers.wait(
            is_blocked,
            timeout=timeout,
            interval=30,
            timeout_msg='Timeout waiting to run the job [{}]'.format(name))
        build_id = self.__client.get_queue_item(num)['executable']['number']

        def is_build_started():
            try:
                build = self.__client.get_build_info(name, build_id)
                ts = float(build['timestamp']) / 1000
                start_time = datetime.datetime.fromtimestamp(ts)
                print("the build {} in {} have started at {} UTC".format(
                    build_id, name, start_time))
                return True
            except jenkins.JenkinsException:
                if verbose:
                    print("the build {} in {} have not strated yet".format(
                        build_id, name))
        helpers.wait(
            is_build_started,
            timeout=timeout,
            interval=30,
            timeout_msg='Timeout waiting to run build of '
                        'the job [{}]'.format(name))

        return name, build_id

    def wait_end_of_build(self, name, build_id, timeout=600, interval=5,
                          verbose=False, job_output_prefix=''):
        '''Wait until the specified build is finished

        :param name: ``str``, job name
        :param build_id: ``int``, build id
        :param timeout: ``int``, timeout waiting the job, sec
        :param interval: ``int``, interval of polling the job result, sec
        :param verbose: ``bool``, print the job console updates during waiting
        :param job_output_prefix: ``str``, print the prefix for each console
                                  output line, with the pre-defined
                                  substitution keys:
                                  - '{name}' : the current job name
                                  - '{build_id}' : the current build-id
                                  - '{time}' : the current time
        :returns: requests object with headers and console output,  ``obj``
        '''
        start = [0]
        time_str = time.strftime("%H:%M:%S")
        prefix = "\n" + job_output_prefix.format(job_name=name,
                                                 build_number=build_id,
                                                 time=time_str)
        if verbose:
            print(prefix, end='')

        def building():
            try:
                status = not self.build_info(name, build_id)['building']
            except ConnectionError:
                status = False

            if verbose:
                time_str = time.strftime("%H:%M:%S")
                prefix = "\n" + job_output_prefix.format(
                    job_name=name, build_number=build_id, time=time_str)
                res = self.get_progressive_build_output(name,
                                                        build_id,
                                                        start=start[0])
                if 'X-Text-Size' in res.headers:
                    text_size = int(res.headers['X-Text-Size'])
                    if start[0] < text_size:
                        text = res.content.decode('utf-8',
                                                  errors='backslashreplace')
                        print(text.replace("\n", prefix), end='')
                        start[0] = text_size
            return status

        helpers.wait(
            building,
            timeout=timeout,
            interval=interval,
            timeout_msg=('Timeout waiting the job {0}:{1} in {2} sec.'
                         .format(name, build_id, timeout)))

    def get_build_output(self, name, build_id):
        return self.__client.get_build_console_output(name, build_id)

    def get_progressive_build_output(self, name, build_id, start=0):
        '''Get build console text.

        :param name: Job name, ``str``
        :param build_id: Build id, ``int``
        :param start: Start offset, ``int``
        :returns: requests object with headers and console output,  ``obj``
        '''
        folder_url, short_name = self.__client._get_job_folder(name)

        PROGRESSIVE_CONSOLE_OUTPUT = (
            '%(folder_url)sjob/%(short_name)s/%(build_id)d/'
            'logText/progressiveText?start=%(start)d')
        req = requests.Request(
                'GET',
                self.__client._build_url(PROGRESSIVE_CONSOLE_OUTPUT, locals()))
        return(self.__client.jenkins_request(req))

    def get_workflow(self, name, build_id, enode=None, mode='describe'):
        '''Get workflow results from pipeline job

        :param name: job name
        :param build_id: str, build number or 'lastBuild'
        :param enode: int, execution node in the workflow
        :param mode: the stage or execution node description if 'describe',
                     the execution node log if 'log'
        '''
        folder_url, short_name = self.__client._get_job_folder(name)

        if enode:
            WORKFLOW_DESCRIPTION = (
                '%(folder_url)sjob/%(short_name)s/%(build_id)s/'
                'execution/node/%(enode)d/wfapi/%(mode)s')
        else:
            WORKFLOW_DESCRIPTION = (
                '%(folder_url)sjob/%(short_name)s/%(build_id)s/wfapi/%(mode)s')
        req = requests.Request(
                'GET',
                self.__client._build_url(WORKFLOW_DESCRIPTION, locals()))
        response = self.__client.jenkins_open(req)
        return json.loads(response)

    def get_artifact(self, name, build_id, artifact_path, destination_name):
        '''Wait until the specified build is finished

        :param name: ``str``, job name
        :param build_id: ``str``, build id or "lastBuild"
        :param artifact_path: ``str``, path and filename of the artifact
                              relative to the job URL
        :param artifact_path: ``str``, destination path and filename
                              on the local filesystem where to save
                              the artifact content
        :returns: requests object with headers and console output,  ``obj``
        '''
        folder_url, short_name = self.__client._get_job_folder(name)

        DOWNLOAD_URL = ('%(folder_url)sjob/%(short_name)s/%(build_id)s/'
                        'artifact/%(artifact_path)s')
        req = requests.Request(
                'GET',
                self.__client._build_url(DOWNLOAD_URL, locals()))

        response = self.__client.jenkins_request(req)
        return response.content
