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


import kubernetes
from kubernetes import client

from tcp_tests.managers.k8s.componentstatuses import \
    K8sComponentStatusManager
from tcp_tests.managers.k8s.daemonsets import K8sDaemonSetManager
from tcp_tests.managers.k8s.deployments import K8sDeploymentManager
from tcp_tests.managers.k8s.endpoints import K8sEndpointsManager
from tcp_tests.managers.k8s.events import K8sEventManager
from tcp_tests.managers.k8s.horizontalpodautoscalers import \
    K8sHorizontalPodAutoscalerManager
from tcp_tests.managers.k8s.ingresses import K8sIngressManager
from tcp_tests.managers.k8s.jobs import K8sJobManager
from tcp_tests.managers.k8s.limitranges import K8sLimitRangeManager
from tcp_tests.managers.k8s.namespaces import K8sNamespaceManager
from tcp_tests.managers.k8s.nodes import K8sNodeManager
from tcp_tests.managers.k8s.persistentvolumeclaims import \
    K8sPersistentVolumeClaimManager
from tcp_tests.managers.k8s.persistentvolumes import \
    K8sPersistentVolumeManager
from tcp_tests.managers.k8s.pods import K8sPodManager
from tcp_tests.managers.k8s.replicationcontrollers import \
    K8sReplicationControllerManager
from tcp_tests.managers.k8s.resourcequotas import K8sResourceQuotaManager
from tcp_tests.managers.k8s.secrets import K8sSecretManager
from tcp_tests.managers.k8s.serviceaccounts import \
    K8sServiceAccountManager
from tcp_tests.managers.k8s.services import K8sServiceManager
from tcp_tests.managers.k8s.replicasets import K8sReplicaSetManager
from tcp_tests.managers.k8s.networkpolicies import K8sNetworkPolicyManager
from tcp_tests.managers.k8s.clusterrolebindings import \
    K8sClusterRoleBindingManager


class K8sCluster(object):
    def __init__(self, schema="https", user=None, password=None, ca=None,
                 host='localhost', port='443', default_namespace='default'):
        self.default_namespace = default_namespace

        api_server = '{0}://{1}:{2}'.format(schema, host, port)

        config_data = {
            'apiVersion': 'v1',
            'kind': 'Config',
            'preferences': {},
            'current-context': 'cluster-remote',
            'clusters': [{
                'name': 'cluster',
                'cluster': {
                    'server': api_server,
                    'certificate-authority-data': ca,
                },
            }],
            'users': [{
                'name': 'remote',
                'user': {
                    'password': password,
                    'username': user,
                },
            }],
            'contexts': [{
                'name': 'cluster-remote',
                'context': {
                    'cluster': 'cluster',
                    'user': 'remote',
                },
            }],
        }

        configuration = type.__call__(client.Configuration)
        loader = kubernetes.config.kube_config.KubeConfigLoader(config_data)
        loader.load_and_set(configuration)
        api_client = client.ApiClient(configuration=configuration)

        self.api_core = client.CoreV1Api(api_client)
        self.api_apps = client.AppsV1Api(api_client)
        self.api_extensions = client.ExtensionsV1beta1Api(api_client)
        self.api_autoscaling = client.AutoscalingV1Api(api_client)
        self.api_batch = client.BatchV1Api(api_client)
        self.api_rbac_auth = client.RbacAuthorizationV1Api(api_client)
        self.api_version = client.VersionApi(api_client)

        self.nodes = K8sNodeManager(self)
        self.pods = K8sPodManager(self)
        self.endpoints = K8sEndpointsManager(self)
        self.namespaces = K8sNamespaceManager(self)
        self.services = K8sServiceManager(self)
        self.serviceaccounts = K8sServiceAccountManager(self)
        self.secrets = K8sSecretManager(self)
        self.events = K8sEventManager(self)
        self.limitranges = K8sLimitRangeManager(self)
        self.jobs = K8sJobManager(self)
        self.daemonsets = K8sDaemonSetManager(self)
        self.ingresses = K8sIngressManager(self)
        self.deployments = K8sDeploymentManager(self)
        self.horizontalpodautoscalers = K8sHorizontalPodAutoscalerManager(self)
        self.componentstatuses = K8sComponentStatusManager(self)
        self.resourcequotas = K8sResourceQuotaManager(self)
        self.replicationcontrollers = K8sReplicationControllerManager(self)
        self.pvolumeclaims = K8sPersistentVolumeClaimManager(self)
        self.pvolumes = K8sPersistentVolumeManager(self)
        self.replicasets = K8sReplicaSetManager(self)
        self.networkpolicies = K8sNetworkPolicyManager(self)
        self.clusterrolebindings = K8sClusterRoleBindingManager(self)
