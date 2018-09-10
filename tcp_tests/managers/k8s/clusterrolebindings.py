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


class K8sClusterRoleBinding(K8sBaseResource):
    resource_type = 'clusterrolebindings'

    def _read(self, **kwargs):
        return self._manager.api.read_cluster_role_binding(self.name, **kwargs)

    def _create(self, body, **kwargs):
        return self._manager.api.create_cluster_role_binding(body, **kwargs)

    def _patch(self, body, **kwargs):
        return self._manager.api.patch_cluster_role_binding(
            self.name, body, **kwargs)

    def _replace(self, body, **kwargs):
        return self._manager.api.replace_cluster_role_binding(
            self.name, body, **kwargs)

    def _delete(self, **kwargs):
        self._manager.api.delete_cluster_role_binding(
            self.name, client.V1DeleteOptions(), **kwargs)


class K8sClusterRoleBindingManager(K8sBaseManager):
    resource_class = K8sClusterRoleBinding

    @property
    def api(self):
        return self._cluster.api_rbac_auth

    def _list(self, namespace, **kwargs):
        return self.api.list_cluster_role_binding(**kwargs)

    def _list_all(self, **kwargs):
        return self._list(None, **kwargs)
