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


from tcp_tests.managers.k8s.base import K8sBaseResource
from tcp_tests.managers.k8s.base import K8sBaseManager


class K8sComponentStatus(K8sBaseResource):
    def _read(self, **kwargs):
        return self._manager.api.read_component_status(self.name, **kwargs)


class K8sComponentStatusManager(K8sBaseManager):
    resource_class = K8sComponentStatus

    @property
    def api(self):
        return self._cluster.api_core

    def _list(self, **kwargs):
        return self.api.list_component_status(**kwargs)
