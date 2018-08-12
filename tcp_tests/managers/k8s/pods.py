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


class K8sPod(K8sBaseResource):
    def _read(self, **kwargs):
        return self._manager.api.read_namespaced_pod(
            self.name, self.namespace, **kwargs)

    def _create(self, body, **kwargs):
        return self._manager.api.create_namespaced_pod(
            self.namespace, body, **kwargs)

    def _patch(self, body, **kwargs):
        return self._manager.api.patch_namespaced_pod(
            self.name, self.namespace, body, **kwargs)

    def _replace(self, body, **kwargs):
        return self._manager.api.replace_namespaced_pod(
            self.name, self.namespace, body, **kwargs)

    def _delete(self, **kwargs):
        self._manager.api.delete_namespaced_pod(
            self.name, self.namespace, client.V1DeleteOptions(), **kwargs)

    def wait_phase(self, phases, timeout=60, interval=3):
        if isinstance(phases, str):
            phases = [phases]

        helpers.wait(lambda: self.read().status.phase in phases,
                     timeout=timeout, interval=interval,
                     timeout_msg='Timeout waiting, pod {0} phase is not in '
                                 '"{1}"'.format(self.name(), phases))
        return self

    def wait_running(self, timeout=240, interval=3):
        return self.wait_phase('Running', timeout=timeout, interval=interval)


class K8sPodManager(K8sBaseManager):
    resource_class = K8sPod

    @property
    def api(self):
        return self._cluster.api_core

    def _list(self, namespace, **kwargs):
        return self.api.list_namespaced_pod(namespace, **kwargs)

    def _list_all(self, **kwargs):
        return self.api.list_pod_for_all_namespaces(**kwargs)
