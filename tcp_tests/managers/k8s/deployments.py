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

from devops.helpers import helpers

from tcp_tests.managers.k8s.base import K8sBaseResource
from tcp_tests.managers.k8s.base import K8sBaseManager


class K8sDeployment(K8sBaseResource):
    resource_type = 'deployment'

    def _read(self, **kwargs):
        return self._manager.api.read_namespaced_deployment(
            self.name, self.namespace, **kwargs)

    def _create(self, body, **kwargs):
        return self._manager.api.create_namespaced_deployment(
            self.namespace, body, **kwargs)

    def _patch(self, body, **kwargs):
        return self._manager.api.patch_namespaced_deployment(
            self.name, self.namespace, body, **kwargs)

    def _replace(self, body, **kwargs):
        return self._manager.api.replace_namespaced_deployment(
            self.name, self.namespace, body, **kwargs)

    def _delete(self, **kwargs):
        self._manager.api.delete_namespaced_deployment(
            self.name, self.namespace, client.V1DeleteOptions(), **kwargs)

    def is_ready(self):
        dep = self.read()
        return dep.status.available_replicas == dep.status.replicas

    def wait_ready(self, timeout=120, interval=5):
        helpers.wait(lambda: self.is_ready(),
                     timeout=timeout, interval=interval)
        return self


class K8sDeploymentManager(K8sBaseManager):
    resource_class = K8sDeployment

    @property
    def api(self):
        return self._cluster.api_apps

    def _list(self, namespace, **kwargs):
        return self.api.list_namespaced_deployment(namespace, **kwargs)

    def _list_all(self, **kwargs):
        return self.api.list_deployment_for_all_namespaces(**kwargs)
