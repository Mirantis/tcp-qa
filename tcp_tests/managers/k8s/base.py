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


import yaml
import requests
import os

from tcp_tests import logger

LOG = logger.logger


class K8sBaseResource(object):
    resource_type = None

    def __init__(self, manager, name=None, namespace=None, data=None):
        self._manager = manager
        self._name = name
        self._namespace = namespace
        self._read_cache = None
        if data is not None:
            self._update_cache(data)

    def __repr__(self):
        uid = 'unknown-uid'
        if self._read_cache is not None:
            uid = self.uid
        return "<{0} name='{1}' namespace='{2}' uuid='{3}'>".format(
            self.__class__.__name__, self.name, self.namespace, uid)

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace or self._cluster.default_namespace

    @property
    def uid(self):
        return self.read(cached=True).metadata.uid

    def _update_cache(self, data):
        self._read_cache = data
        self._namespace = data.metadata.namespace
        self._name = data.metadata.name

    def read(self, cached=False, **kwargs):
        if not cached:
            self._update_cache(self._read(**kwargs))
        return self._read_cache

    def create(self, body, **kwargs):
        LOG.info("K8S API Creating {0} with body:\n{1}".format(
                 self.resource_type, body))

        self._update_cache(self._create(body, **kwargs))
        return self

    def patch(self, body, **kwargs):

        LOG.info("K8S API Patching {0} name={1} ns={2} with body:\n{3}".format(
                 self.resource_type, self.name, self.namespace, body))

        self._update_cache(self._patch(body, **kwargs))
        return self

    def replace(self, body, **kwargs):
        self._update_cache(self._replace(body, **kwargs))
        return self

    def delete(self, **kwargs):
        self._delete(**kwargs)
        return self

    def __eq__(self, other):
        if not isinstance(other, K8sBaseResource):
            return NotImplemented

        if not isinstance(other, self.__class__):
            return False

        return self.uid == other.uid


class K8sBaseManager(object):
    resource_class = None

    def __init__(self, cluster):
        self._cluster = cluster

    @property
    def resource_type(self):
        return self.resource_class.resource_type

    def get(self, name=None, namespace=None, data=None):
        namespace = namespace or self._cluster.default_namespace
        return self.resource_class(self, name, namespace, data)

    def create(self, name=None, namespace=None, body=None, **kwargs):
        return self.get(name=name, namespace=namespace).create(body, **kwargs)

    def __resource_from_data(self, data):
        return self.resource_class(self, data=data)

    def __list_filter(self, items, name_prefix=None):
        if name_prefix is not None:
            items = [item for item in items if
                     item.metadata.name.startswith(name_prefix)]
        return items

    def __list_to_resource(self, items):
        return [self.__resource_from_data(item) for item in items]

    def list(self, namespace=None, name_prefix=None, **kwargs):
        namespace = namespace or self._cluster.default_namespace
        items = self._list(namespace=namespace, **kwargs).items
        items = self.__list_filter(items, name_prefix=name_prefix)
        return self.__list_to_resource(items)

    def list_all(self, name_prefix=None, **kwargs):
        items = self._list_all(**kwargs).items
        items = self.__list_filter(items, name_prefix=name_prefix)
        return self.__list_to_resource(items)


def read_yaml_str(yaml_str):
    """ load yaml from string helper """
    return yaml.safe_load(yaml_str)


def read_yaml_file(file_path, *args):
    """ load yaml from joined file_path and *args helper """
    with open(os.path.join(file_path, *args)) as f:
        return yaml.safe_load(f)


def read_yaml_url(yaml_file_url):
    """ load yaml from url helper """
    return yaml.safe_load(requests.get(yaml_file_url).text)
