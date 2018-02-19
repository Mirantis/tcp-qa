import time

import jenkins

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

    def run_build(self, name, params=None):
        params = params or self.make_defults_params(name)
        self.__client.build_job(name, params)
        time.sleep(10)  # wait while jobs started:
        build_id = self.job_info(name)['lastBuild']['number']
        return name, build_id

    def wait_end_of_build(self, name, build_id, timeout=600):

        def building():
            return not self.build_info(name, build_id)['building']

        helpers.wait(
            building,
            timeout=timeout,
            timeout_msg='Timeout waiting, job {0} are not finished "{1}" build'
                        ' still'.format(name, build_id))

    def get_build_output(self, name, build_id):
        return self.__client.get_build_console_output(name, build_id)
