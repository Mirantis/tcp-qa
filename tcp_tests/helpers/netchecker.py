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
#    under the License.

import requests

from devops.helpers import helpers

from tcp_tests import logger
from tcp_tests.helpers import utils


LOG = logger.logger

NETCHECKER_NAMESPACE = "netchecker"
NETCHECKER_SERVICE_PREFIX = "netchecker"
NETCHECKER_SERVER_PREFIX = "netchecker-server-"
NETCHECKER_AGENT_PREFIX = "netchecker-agent-"


class Netchecker(object):
    def __init__(self, k8sapi, namespace=NETCHECKER_NAMESPACE):
        self._api = k8sapi
        self._namespace = namespace

    def get_netchecker_pod_ip(self, prefix=NETCHECKER_SERVER_PREFIX):
        pods = self._api.pods.list(self._namespace, name_prefix=prefix)
        assert len(pods) > 0, "No '{}' pods found!".format(prefix)
        return pods[0].read().status.host_ip

    def get_netchecker_service(self, prefix=NETCHECKER_SERVICE_PREFIX):
        services = self._api.services.list(self._namespace, name_prefix=prefix)
        assert len(services) > 0, "No '{}' services found!".format(prefix)
        return services[0]

    @utils.retry(3, requests.exceptions.RequestException)
    def get_connectivity_status(self):
        kube_host_ip = self.get_netchecker_pod_ip()

        net_status_url = 'http://{0}:{1}/api/v1/connectivity_check'.format(
            kube_host_ip, self.get_service_port())

        response = requests.get(net_status_url, timeout=5)
        LOG.debug('Connectivity check status: [{0}] {1}'.format(
            response.status_code, response.text.strip()))
        return response

    @utils.retry(3, requests.exceptions.RequestException)
    def wait_netchecker_pods_running(self, prefix):
        for pod in self._api.pods.list(self._namespace, name_prefix=prefix):
            pod.wait_running(timeout=600)

    def check_network(self, works):
        if works:
            assert self.get_connectivity_status().status_code in (200, 204)
        else:
            assert self.get_connectivity_status().status_code == 400

    def wait_check_network(self, works, timeout=600, interval=10):
        helpers.wait_pass(
            lambda: self.check_network(works=works),
            timeout=timeout,
            interval=interval)

    def kubernetes_block_traffic_namespace(self,
                                           namespace=NETCHECKER_NAMESPACE):
        self._api.namespaces.get(name=namespace).patch({
            "metadata": {
                "annotations": {
                    "net.beta.kubernetes.io/network-policy":
                        '{"ingress": {"isolation": "DefaultDeny"}}',
                }
            }
        })

    def calico_allow_netchecker_connections(self):
        srv_pod_ip = self.get_netchecker_pod_ip()

        body = {
            "apiVersion": "extensions/v1beta1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": "access-netchecker",
                "namespace": self._namespace,
            },
            "spec": {
                "ingress": [{
                    "from": [{
                        "ipBlock": {
                            "cidr": srv_pod_ip + "/24"
                        }
                    }]
                }],
                "podSelector": {
                    "matchLabels": {
                        "app": "netchecker-server"
                    }
                }
            }
        }

        self._api.networkpolicies.create(namespace=self._namespace, body=body)

    def kubernetes_allow_traffic_from_agents(self):
        self._api.namespaces.get('default').patch({
            "metadata": {
                "labels": {
                    "name": 'default',
                    "net.beta.kubernetes.io/network-policy": None,
                }
            }
        })

        kubernetes_policy = {
            "apiVersion": "extensions/v1beta1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": "access-netchecker-agent",
                "namespace": self._namespace,
            },
            "spec": {
                "ingress": [
                    {
                        "from": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {
                                        "name": self._namespace
                                    }
                                }
                            },
                            {
                                "podSelector": {
                                    "matchLabels": {
                                        "app": "netchecker-agent"
                                    }
                                }
                            }
                        ]
                    }
                ],
                "podSelector": {
                    "matchLabels": {
                        "app": "netchecker-server"
                    }
                }
            }
        }

        kubernetes_policy_hostnet = {
            "apiVersion": "extensions/v1beta1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": "access-netchecker-agent-hostnet",
                "namespace": self._namespace,
            },
            "spec": {
                "ingress": [
                    {
                        "from": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {
                                        "name": self._namespace
                                    }
                                }
                            },
                            {
                                "podSelector": {
                                    "matchLabels": {
                                        "app": "netchecker-agent-hostnet"
                                    }
                                }
                            }
                        ]
                    }
                ],
                "podSelector": {
                    "matchLabels": {
                        "app": "netchecker-server"
                    }
                }
            }
        }

        self._api.networkpolicies.create(
            namespace=self._namespace, body=kubernetes_policy)
        self._api.networkpolicies.create(
            namespace=self._namespace, body=kubernetes_policy_hostnet)

    @utils.retry(3, requests.exceptions.RequestException)
    def get_metric(self):
        kube_host_ip = self.get_netchecker_pod_ip()

        metrics_url = 'http://{0}:{1}/metrics'.format(
            kube_host_ip, self.get_service_port())

        response = requests.get(metrics_url, timeout=30)
        LOG.debug('Metrics: [{0}] {1}'.format(
            response.status_code, response.text.strip()))
        return response

    def get_service_port(self):
        service_details = self.get_netchecker_service()
        LOG.debug('Netchecker service details {0}'.format(service_details))
        return service_details.read().spec.ports[0].node_port
