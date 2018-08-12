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
import six
import requests


class K8sBaseResource(object):
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
        return self.namespace or self._cluster.default_namespace

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
        return self.__read_cache

    def create(self, body=None, file_path=None, url=None, **kwargs):
        if isinstance(body, six.string_types):
            body = yaml.safe_load(body)
        elif file_path is not None:
            with open(file_path) as f:
                body = yaml.safe_load(f)
        elif url is not None:
            body = yaml.safe_load(requests.get(url).text)
        elif body is None:
            raise ValueError("Missed argument")

        if self._name is not None:
            if 'metadata' not in body:
                body['metadata'] = dict()
            body['metadata']['name'] = self._name

        self._update_cache(self._create(body, **kwargs))
        return self

    def patch(self, body, **kwargs):
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

    def get(self, name=None, namespace=None, data=None):
        namespace = namespace or self._cluster.default_namespace
        return self.resource_class(self, name, namespace, data)

    def __resource_from_data(self, data):
        return self.resource_class(self, data=data)

    def __list_filter(self, items, name_prefix=None):
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
