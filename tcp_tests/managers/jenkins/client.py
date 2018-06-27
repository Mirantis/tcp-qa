from __future__ import print_function
import time

import jenkins
import requests

from devops.helpers import helpers


class JenkinsWrapper(jenkins.Jenkins):
    """Workaround for the bug:
       https://bugs.launchpad.net/python-jenkins/+bug/1775047
    """
    def _response_handler(self, response):
        '''Handle response objects'''

        # raise exceptions if occurred
        response.raise_for_status()

        headers = response.headers
        if (headers.get('content-length') is None and
                headers.get('transfer-encoding') is None and
                (response.status_code == 201 and
                 headers.get('location') is None) and
                (response.content is None or len(response.content) <= 0)):
            # response body should only exist if one of these is provided
            raise jenkins.EmptyResponseException(
                "Error communicating with server[%s]: "
                "empty response" % self.server)

        # Response objects will automatically return unicode encoded
        # when accessing .text property
        return response


class JenkinsClient(object):

    def __init__(self, host=None, username=None, password=None):
        host = host or 'http://172.16.44.33:8081'
        username = username or 'admin'
        password = password or 'r00tme'
        # self.__client = jenkins.Jenkins(
        self.__client = JenkinsWrapper(
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
        time.sleep(20)  # wait while job is started

        #def is_blocked():
        #    queued = self.__client.get_queue_item(num)
        #    status = not queued['blocked']
        #    if not status and verbose:
        #        print("pending the job [{}] : {}".format(name, queued['why']))
        #    return (status and
        #            'executable' in (queued or {}) and
        #            'number' in (queued['executable'] or {}))

       # helpers.wait(
       #     is_blocked,
       #     timeout=timeout,
       #     interval=30,
       #     timeout_msg='Timeout waiting to run the job [{}]'.format(name))
       # build_id = self.__client.get_queue_item(num)['executable']['number']
       # return name, build_id

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
            status = not self.build_info(name, build_id)['building']
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
            timeout_msg='Timeout waiting, job {0} are not finished "{1}" build'
                        ' still'.format(name, build_id))

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
