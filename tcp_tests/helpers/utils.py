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

import copy
import os
import shutil
import StringIO
import time
import traceback
import signal

import jinja2
import paramiko
import yaml
from devops.helpers import ssh_client

from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


def get_test_method_name():
    raise NotImplementedError


def update_yaml(yaml_tree=None, yaml_value='', is_uniq=True,
                yaml_file=settings.TIMESTAT_PATH_YAML, remote=None):
    """Store/update a variable in YAML file.

    yaml_tree - path to the variable in YAML file, will be created if absent,
    yaml_value - value of the variable, will be overwritten if exists,
    is_uniq - If false, add the unique two-digit suffix to the variable name.
    """
    def get_file(path, remote=None, mode="r"):
        if remote:
            return remote.open(path, mode)
        else:
            return open(path, mode)

    if yaml_tree is None:
        yaml_tree = []
    with get_file(yaml_file, remote) as file_obj:
        yaml_data = yaml.safe_load(file_obj)

    # Walk through the 'yaml_data' dict, find or create a tree using
    # sub-keys in order provided in 'yaml_tree' list
    item = yaml_data
    for n in yaml_tree[:-1]:
        if n not in item:
            item[n] = {}
        item = item[n]

    if is_uniq:
        last = yaml_tree[-1]
    else:
        # Create an uniq suffix in range '_00' to '_99'
        for n in range(100):
            last = str(yaml_tree[-1]) + '_' + str(n).zfill(2)
            if last not in item:
                break

    item[last] = yaml_value
    with get_file(yaml_file, remote, mode='w') as file_obj:
        yaml.dump(yaml_data, file_obj, default_flow_style=False)


class TimeStat(object):
    """Context manager for measuring the execution time of the code.

    Usage:
    with TimeStat([name],[is_uniq=True]):
    """

    def __init__(self, name=None, is_uniq=False):
        if name:
            self.name = name
        else:
            self.name = 'timestat'
        self.is_uniq = is_uniq
        self.begin_time = 0
        self.end_time = 0
        self.total_time = 0

    def __enter__(self):
        self.begin_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.end_time = time.time()
        self.total_time = self.end_time - self.begin_time

        # Create a path where the 'self.total_time' will be stored.
        yaml_path = []

        # There will be a list of one or two yaml subkeys:
        # - first key name is the method name of the test
        method_name = get_test_method_name()
        if method_name:
            yaml_path.append(method_name)

        # - second (subkey) name is provided from the decorator (the name of
        # the just executed function), or manually.
        yaml_path.append(self.name)

        try:
            update_yaml(yaml_path, '{:.2f}'.format(self.total_time),
                        self.is_uniq)
        except Exception:
            LOG.error("Error storing time statistic for {0}"
                      " {1}".format(yaml_path, traceback.format_exc()))
            raise

    @property
    def spent_time(self):
        return time.time() - self.begin_time


def reduce_occurrences(items, text):
    """ Return string without items(substrings)
        Args:
            items: iterable of strings
            test: string
        Returns:
            string
        Raise:
            AssertionError if any substing not present in source text
    """
    for item in items:
        LOG.debug(
            "Verifying string {} is shown in "
            "\"\"\"\n{}\n\"\"\"".format(item, text))
        assert text.count(item) != 0
        text = text.replace(item, "", 1)
    return text


def generate_keys():
    file_obj = StringIO.StringIO()
    key = paramiko.RSAKey.generate(1024)
    key.write_private_key(file_obj)
    public = key.get_base64()
    private = file_obj.getvalue()
    file_obj.close()
    return {'private': private,
            'public': public}


def load_keyfile(file_path):
    with open(file_path, 'r') as private_key_file:
        private = private_key_file.read()
    key = paramiko.RSAKey(file_obj=StringIO.StringIO(private))
    public = key.get_base64()
    return {'private': private,
            'public': public}


def dump_keyfile(file_path, key):
    key = paramiko.RSAKey(file_obj=StringIO.StringIO(key['private']))
    key.write_private_key_file(file_path)
    os.chmod(file_path, 0o644)


def clean_dir(dirpath):
    shutil.rmtree(dirpath)


def retry(tries_number=2, exception=Exception):
    def _retry(func):
        assert tries_number >= 1, 'ERROR! @retry is called with no tries!'

        def wrapper(*args, **kwargs):
            iter_number = 1
            while True:
                try:
                    LOG.debug('Calling function "{0}" with args "{1}" and '
                              'kwargs "{2}". Try # {3}.'.format(func.__name__,
                                                                args,
                                                                kwargs,
                                                                iter_number))
                    return func(*args, **kwargs)
                except exception as e:
                    if iter_number > tries_number:
                        LOG.debug('Failed to execute function "{0}" with {1} '
                                  'tries!'.format(func.__name__, tries_number))
                        raise e
                iter_number += 1
        return wrapper
    return _retry


class YamlEditor(object):
    """Manipulations with local or remote .yaml files.

    Usage:

    with YamlEditor("tasks.yaml") as editor:
        editor.content[key] = "value"

    with YamlEditor("astute.yaml", ip=self.admin_ip) as editor:
        editor.content[key] = "value"
    """

    def __init__(self, file_path, host=None, port=None,
                 username=None, password=None, private_keys=None,
                 document_id=0,
                 default_flow_style=False, default_style=None):
        self.__file_path = file_path
        self.host = host
        self.port = port or 22
        self.username = username
        self.__password = password
        self.__private_keys = private_keys or []
        self.__content = None
        self.__documents = [{}, ]
        self.__document_id = document_id
        self.__original_content = None
        self.default_flow_style = default_flow_style
        self.default_style = default_style

    @property
    def file_path(self):
        """Open file path

        :rtype: str
        """
        return self.__file_path

    @property
    def content(self):
        if self.__content is None:
            self.__content = self.get_content()
        return self.__content

    @content.setter
    def content(self, new_content):
        self.__content = new_content

    def __get_file(self, mode="r"):
        if self.host:
            remote = ssh_client.SSHClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.__password,
                private_keys=self.__private_keys)

            return remote.open(self.__file_path, mode=mode)
        else:
            return open(self.__file_path, mode=mode)

    def get_content(self):
        """Return a single document from YAML"""
        def multi_constructor(loader, tag_suffix, node):
            """Stores all unknown tags content into a dict

            Original yaml:
            !unknown_tag
            - some content

            Python object:
            {"!unknown_tag": ["some content", ]}
            """
            if type(node.value) is list:
                if type(node.value[0]) is tuple:
                    return {node.tag: loader.construct_mapping(node)}
                else:
                    return {node.tag: loader.construct_sequence(node)}
            else:
                return {node.tag: loader.construct_scalar(node)}

        yaml.add_multi_constructor("!", multi_constructor)
        with self.__get_file() as file_obj:
            self.__documents = [x for x in yaml.load_all(file_obj)]
            return self.__documents[self.__document_id]

    def write_content(self, content=None):
        if content:
            self.content = content
        self.__documents[self.__document_id] = self.content

        def representer(dumper, data):
            """Represents a dict key started with '!' as a YAML tag

            Assumes that there is only one !tag in the dict at the
            current indent.

            Python object:
            {"!unknown_tag": ["some content", ]}

            Resulting yaml:
            !unknown_tag
            - some content
            """
            key = data.keys()[0]
            if key.startswith("!"):
                value = data[key]
                if type(value) is dict:
                    node = dumper.represent_mapping(key, value)
                elif type(value) is list:
                    node = dumper.represent_sequence(key, value)
                else:
                    node = dumper.represent_scalar(key, value)
            else:
                node = dumper.represent_mapping(u'tag:yaml.org,2002:map', data)
            return node

        yaml.add_representer(dict, representer)
        with self.__get_file("w") as file_obj:
            yaml.dump_all(self.__documents, file_obj,
                          default_flow_style=self.default_flow_style,
                          default_style=self.default_style)

    def __enter__(self):
        self.__content = self.get_content()
        self.__original_content = copy.deepcopy(self.content)
        return self

    def __exit__(self, x, y, z):
        if self.content == self.__original_content:
            return
        self.write_content()


def render_template(file_path, options=None, log_env_vars=True):
    required_env_vars = set()
    optional_env_vars = dict()

    def os_env(var_name, default=None):
        var = os.environ.get(var_name, default)

        if var is None:
            raise Exception("Environment variable '{0}' is undefined!"
                            .format(var_name))

        if default is None:
            required_env_vars.add(var_name)
        else:
            optional_env_vars[var_name] = var

        return var

    if options is None:
        options = {}
    options.update({'os_env': os_env, })

    LOG.info("Reading template {0}".format(file_path))

    path, filename = os.path.split(file_path)
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader([path, os.path.dirname(path)],
                                       followlinks=True))
    template = environment.get_template(filename).render(options)

    if required_env_vars and log_env_vars:
        LOG.info("Required environment variables:")
        for var in required_env_vars:
            LOG.info("    {0}".format(var))
    if optional_env_vars and log_env_vars:
        LOG.info("Optional environment variables:")
        for var, default in sorted(optional_env_vars.iteritems()):
            LOG.info("    {0} , value = {1}".format(var, default))
    return template


def extract_name_from_mark(mark):
    """Simple function to extract name from pytest mark

    :param mark: pytest.mark.MarkInfo
    :rtype: string or None
    """
    if mark:
        if len(mark.args) > 0:
            return mark.args[0]
        elif 'name' in mark.kwargs:
            return mark.kwargs['name']
    return None


def get_top_fixtures_marks(request, mark_name):
    """Order marks according to fixtures order

    When a test use fixtures that depend on each other in some order,
    that fixtures can have the same pytest mark.

    This method extracts such marks from fixtures that are used in the
    current test and return the content of the marks ordered by the
    fixture dependences.
    If the test case have the same mark, than the content of this mark
    will be the first element in the resulting list.

    :param request: pytest 'request' fixture
    :param mark_name: name of the mark to search on the fixtures and the test

    :rtype list: marks content, from last to first executed.
    """

    fixtureinfo = request.session._fixturemanager.getfixtureinfo(
        request.node, request.function, request.cls)

    top_fixtures_names = []
    for _ in enumerate(fixtureinfo.name2fixturedefs):
        parent_fixtures = set()
        child_fixtures = set()
        for name in sorted(fixtureinfo.name2fixturedefs):
            if name in top_fixtures_names:
                continue
            parent_fixtures.add(name)
            child_fixtures.update(
                fixtureinfo.name2fixturedefs[name][0].argnames)
        top_fixtures_names.extend(list(parent_fixtures - child_fixtures))

    top_fixtures_marks = []

    if mark_name in request.function.func_dict:
        # The top priority is the 'revert_snapshot' mark on the test
        top_fixtures_marks.append(
            extract_name_from_mark(
                request.function.func_dict[mark_name]))

    for top_fixtures_name in top_fixtures_names:
        fd = fixtureinfo.name2fixturedefs[top_fixtures_name][0]
        if mark_name in fd.func.func_dict:
            fixture_mark = extract_name_from_mark(
                fd.func.func_dict[mark_name])
            # Append the snapshot names in the order that fixtures are called
            # starting from the last called fixture to the first one
            top_fixtures_marks.append(fixture_mark)

    LOG.debug("Fixtures ordered from last to first called: {0}"
              .format(top_fixtures_names))
    LOG.debug("Marks ordered from most to least preffered: {0}"
              .format(top_fixtures_marks))

    return top_fixtures_marks


class RunLimit(object):
    def __init__(self, seconds=60, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutException(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, value, traceback):
        signal.alarm(0)


class TimeoutException(Exception):
    pass
