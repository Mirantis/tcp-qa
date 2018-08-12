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


from kubernetes import client

from tcp_tests.managers.k8s.base import K8sBaseResource
from tcp_tests.managers.k8s.base import K8sBaseManager


class K8sNode(K8sBaseResource):
    resource_type = 'node'

    def _read(self, **kwargs):
        return self._manager.api.read_node(self.name, **kwargs)

    def _create(self, body, **kwargs):
        return self._manager.api.create_node(body, **kwargs)

    def _patch(self, body, **kwargs):
        return self._manager.api.patch_node(self.name, body, **kwargs)

    def _replace(self, body, **kwargs):
        return self._manager.api.replace_node(self.name, body, **kwargs)

    def _delete(self, **kwargs):
        self._manager.api.delete_node(
            self.name, client.V1DeleteOptions(), **kwargs)


class K8sNodeManager(K8sBaseManager):
    resource_class = K8sNode

    @property
    def api(self):
        return self._cluster.api_core

    def _list(self, namespace, **kwargs):
        return self.api.list_node(**kwargs)

    def _list_all(self, **kwargs):
        return self._list(None, **kwargs)
