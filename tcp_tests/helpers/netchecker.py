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

import json
import requests

from devops.helpers import helpers
from k8sclient.client import rest

from tcp_tests import logger
from tcp_tests.helpers import utils


LOG = logger.logger


NETCHECKER_SERVICE_NAME = "netchecker-service"
NETCHECKER_CONTAINER_PORT = NETCHECKER_SERVICE_PORT = 8081
NETCHECKER_NODE_PORT = 31081
NETCHECKER_REPORT_INTERVAL = 30
NETCHECKER_SERVER_REPLICAS = 1
NETCHECKER_PROBEURLS = "http://ipinfo.io"

NETCHECKER_SVC_CFG = {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
        "name": NETCHECKER_SERVICE_NAME
    },
    "spec": {
        "ports": [
            {
                "nodePort": NETCHECKER_NODE_PORT,
                "port": NETCHECKER_SERVICE_PORT,
                "protocol": "TCP",
                "targetPort": NETCHECKER_CONTAINER_PORT
            }
        ],
        "selector": {
            "app": "netchecker-server"
        },
        "type": "NodePort"
    }
}

NETCHECKER_DEPLOYMENT_CFG = {
    "kind": "Deployment",
    "spec": {
        "template": {
            "spec": {
                "containers": [
                    {
                        "name": "netchecker-server",
                        "env": None,
                        "imagePullPolicy": "IfNotPresent",
                        "image": "mirantis/k8s-netchecker-server:latest",
                        "args": [
                            "-v=5",
                            "-logtostderr",
                            "-kubeproxyinit",
                            "-endpoint=0.0.0.0:{0}".format(
                                NETCHECKER_CONTAINER_PORT)
                        ],
                        "ports": [
                            {
                                "containerPort": NETCHECKER_CONTAINER_PORT,
                                "hostPort": NETCHECKER_NODE_PORT
                            }
                        ]
                    }
                ]
            },
            "metadata": {
                "labels": {
                    "app": "netchecker-server"
                },
                "name": "netchecker-server"
            }
        },
        "replicas": NETCHECKER_SERVER_REPLICAS
    },
    "apiVersion": "extensions/v1beta1",
    "metadata": {
        "name": "netchecker-server"
    }
}

NETCHECKER_DS_CFG = [
    {
        "apiVersion": "extensions/v1beta1",
        "kind": "DaemonSet",
        "metadata": {
            "labels": {
                "app": "netchecker-agent"
            },
            "name": "netchecker-agent"
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {
                        "app": "netchecker-agent"
                    },
                    "name": "netchecker-agent"
                },
                "spec": {
                    "tolerations": [
                        {
                            "key": "node-role.kubernetes.io/master",
                            "effect": "NoSchedule"
                        }
                    ],
                    "containers": [
                        {
                            "env": [
                                {
                                    "name": "MY_POD_NAME",
                                    "valueFrom": {
                                        "fieldRef": {
                                            "fieldPath": "metadata.name"
                                        }
                                    }
                                },
                                {
                                    "name": "MY_NODE_NAME",
                                    "valueFrom": {
                                        "fieldRef": {
                                            "fieldPath": "spec.nodeName"
                                        }
                                    }
                                },
                                {
                                    "name": "REPORT_INTERVAL",
                                    "value": str(NETCHECKER_REPORT_INTERVAL)
                                },
                            ],
                            "image": "mirantis/k8s-netchecker-agent:latest",
                            "imagePullPolicy": "IfNotPresent",
                            "name": "netchecker-agent",
                            "command": ["netchecker-agent"],
                            "args": [
                                "-v=5",
                                "-logtostderr",
                                "-probeurls={0}".format(NETCHECKER_PROBEURLS)
                            ]
                        }
                    ],
                }
            },
            "updateStrategy": {
                "type": "RollingUpdate"
            }
        }
    },
    {
        "apiVersion": "extensions/v1beta1",
        "kind": "DaemonSet",
        "metadata": {
            "labels": {
                "app": "netchecker-agent-hostnet"
            },
            "name": "netchecker-agent-hostnet"
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {
                        "app": "netchecker-agent-hostnet"
                    },
                    "name": "netchecker-agent-hostnet"
                },
                "spec": {
                    "tolerations": [
                        {
                            "key": "node-role.kubernetes.io/master",
                            "effect": "NoSchedule"
                        }
                    ],
                    "containers": [
                        {
                            "env": [
                                {
                                    "name": "MY_POD_NAME",
                                    "valueFrom": {
                                        "fieldRef": {
                                            "fieldPath": "metadata.name"
                                        }
                                    }
                                },
                                {
                                    "name": "MY_NODE_NAME",
                                    "valueFrom": {
                                        "fieldRef": {
                                            "fieldPath": "spec.nodeName"
                                        }
                                    }
                                },
                                {
                                    "name": "REPORT_INTERVAL",
                                    "value": str(NETCHECKER_REPORT_INTERVAL)
                                },
                            ],
                            "image": "mirantis/k8s-netchecker-agent:latest",
                            "imagePullPolicy": "IfNotPresent",
                            "name": "netchecker-agent",
                            "command": ["netchecker-agent"],
                            "args": [
                                "-v=5",
                                "-logtostderr",
                                "-probeurls={0}".format(NETCHECKER_PROBEURLS)
                            ]
                        }
                    ],
                    "hostNetwork": True,
                    "dnsPolicy": "ClusterFirstWithHostNet",
                    "updateStrategy": {
                        "type": "RollingUpdate"
                    }
                }
            },
            "updateStrategy": {
                "type": "RollingUpdate"
            }
        }
    }
]

NETCHECKER_BLOCK_POLICY = {
    "kind": "policy",
    "spec": {
        "ingress": [
            {
                "action": "allow"
            },
            {
                "action": "deny",
                "destination": {
                    "ports": [
                        NETCHECKER_SERVICE_PORT
                    ]
                },
                "protocol": "tcp"
            }
        ]
    },
    "apiVersion": "v1",
    "metadata": {
        "name": "deny-netchecker"
    }
}


def start_server(k8s, config, namespace=None,
                 deploy_spec=NETCHECKER_DEPLOYMENT_CFG,
                 svc_spec=NETCHECKER_SVC_CFG):
    """Start netchecker server in k8s cluster

    :param k8s: K8SManager
    :param config: fixture provides oslo.config
    :param namespace: str
    :param deploy_spec: dict
    :param svc_spec: dict
    :return: None
    """
    for container in deploy_spec['spec']['template']['spec']['containers']:
        if container['name'] == 'netchecker-server':
            container['image'] = \
                config.k8s_deploy.kubernetes_netchecker_server_image
    try:
        if k8s.api.deployments.get(name=deploy_spec['metadata']['name'],
                                   namespace=namespace):
            LOG.debug('Network checker server deployment "{}" '
                      'already exists! Skipping resource '
                      'creation'.format(deploy_spec['metadata']['name']))
    except rest.ApiException as e:
        if e.status == 404:
            n = k8s.check_deploy_create(body=deploy_spec, namespace=namespace)
            k8s.wait_deploy_ready(n.name, namespace=namespace)
        else:
            raise e
    try:
        if k8s.api.services.get(name=svc_spec['metadata']['name']):
            LOG.debug('Network checker server service {} is '
                      'already running! Skipping resource creation'
                      '.'.format(svc_spec['metadata']['name']))
    except rest.ApiException as e:
        if e.status == 404:
            k8s.check_service_create(body=svc_spec, namespace=namespace)
        else:
            raise e


def start_agent(k8s, config, namespace=None, ds_spec=NETCHECKER_DS_CFG,
                service_namespace=None):
    """Start netchecker agent in k8s cluster

    :param k8s: K8SManager
    :param config: fixture provides oslo.config
    :param namespace: str
    :param ds_spec: str
    :return: None
    """
    for ds in ds_spec:
        for container in ds['spec']['template']['spec']['containers']:
            if container['name'] == 'netchecker-agent':
                container['image'] = \
                    config.k8s_deploy.kubernetes_netchecker_agent_image
                if service_namespace is not None:
                    container['args'].append(
                        "-serverendpoint={0}.{1}.svc.cluster.local:{2}".format(
                            NETCHECKER_SERVICE_NAME,
                            service_namespace,
                            NETCHECKER_SERVICE_PORT))
        k8s.check_ds_create(body=ds, namespace=namespace)
        k8s.wait_ds_ready(dsname=ds['metadata']['name'], namespace=namespace)
    k8s.wait_pods_phase(pods=[pod for pod in k8s.api.pods.list()
                              if 'netchecker-agent' in pod.name],
                        phase='Running',
                        timeout=600)


@utils.retry(3, requests.exceptions.RequestException)
def get_connectivity_status(k8sclient,
                            netchecker_pod_port=NETCHECKER_NODE_PORT,
                            pod_name='netchecker-server', namespace='default'):

    netchecker_srv_pod_names = [pod.name for pod in
                                k8sclient.pods.list(namespace=namespace)
                                if pod_name in pod.name]

    assert len(netchecker_srv_pod_names) > 0, \
        "No netchecker-server pods found!"

    netchecker_srv_pod = k8sclient.pods.get(name=netchecker_srv_pod_names[0],
                                            namespace=namespace)
    kube_host_ip = netchecker_srv_pod.status.host_ip
    net_status_url = 'http://{0}:{1}/api/v1/connectivity_check'.format(
        kube_host_ip, netchecker_pod_port)
    response = requests.get(net_status_url, timeout=5)
    LOG.debug('Connectivity check status: [{0}] {1}'.format(
        response.status_code, response.text.strip()))
    return response


@utils.retry(3, requests.exceptions.RequestException)
def get_netchecker_pod_status(k8s,
                              pod_name='netchecker-server',
                              namespace='default'):

    k8s.wait_pods_phase(
        pods=[pod for pod in k8s.api.pods.list(namespace=namespace)
              if pod_name in pod.name], phase='Running', timeout=600)


def check_network(k8sclient, netchecker_pod_port,
                  namespace='default', works=True):
    if works:
        assert get_connectivity_status(
            k8sclient, namespace=namespace,
            netchecker_pod_port=netchecker_pod_port).status_code in (200, 204)
    else:
        assert get_connectivity_status(
            k8sclient, namespace=namespace,
            netchecker_pod_port=netchecker_pod_port).status_code == 400


def wait_check_network(k8sclient, namespace='default', works=True, timeout=300,
                       interval=10, netchecker_pod_port=NETCHECKER_NODE_PORT):
    helpers.wait_pass(
        lambda: check_network(
            k8sclient, netchecker_pod_port=netchecker_pod_port,
            namespace=namespace,
            works=works),
        timeout=timeout,
        interval=interval)


def calico_block_traffic_on_node(underlay, target_node):
    cmd = "echo '{0}' | calicoctl create -f -".format(NETCHECKER_BLOCK_POLICY)
    underlay.sudo_check_call(cmd, node_name=target_node)
    LOG.info('Blocked traffic to the network checker service from '
             'containers on node "{}".'.format(target_node))


def calico_unblock_traffic_on_node(underlay, target_node):
    cmd = "echo '{0}' | calicoctl delete -f -".format(NETCHECKER_BLOCK_POLICY)

    underlay.sudo_check_call(cmd, node_name=target_node)
    LOG.info('Unblocked traffic to the network checker service from '
             'containers on node "{}".'.format(target_node))


def calico_get_version(underlay, target_node):
    raw_version = underlay.sudo_check_call('calicoctl version',
                                           node_name=target_node)

    assert raw_version['exit_code'] == 0 and len(raw_version['stdout']) > 0, \
        "Unable to get calico version!"

    if len(raw_version['stdout']) > 1:
        ctl_version = raw_version['stdout'][0].split()[1].strip()
    else:
        ctl_version = raw_version['stdout'][0].strip()

    LOG.debug("Calico (calicoctl) version on '{0}': '{1}'".format(target_node,
                                                                  ctl_version))
    return ctl_version


def kubernetes_block_traffic_namespace(underlay, kube_host_ip, namespace):
    # TODO(apanchenko): do annotation using kubernetes API
    cmd = ('kubectl annotate ns {0} \'net.beta.kubernetes.io/'
           'network-policy={{"ingress": {{"isolation":'
           ' "DefaultDeny"}}}}\'').format(namespace)
    underlay.sudo_check_call(cmd=cmd, host=kube_host_ip)


def calico_allow_netchecker_connections(underlay, k8sclient, kube_host_ip,
                                        namespace):
    netchecker_srv_pod_names = [pod.name for pod in
                                k8sclient.pods.list(namespace=namespace)
                                if 'netchecker-server' in pod.name]

    assert len(netchecker_srv_pod_names) > 0, \
        "No netchecker-server pods found!"

    netchecker_srv_pod = k8sclient.pods.get(name=netchecker_srv_pod_names[0],
                                            namespace=namespace)
    nc_host_ip = netchecker_srv_pod.status.host_ip

    kubernetes_policy = {
        "apiVersion": "extensions/v1beta1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": "access-netchecker",
            "namespace": namespace,
        },
        "spec": {
            "ingress": [
                {
                    "from": [
                        {
                            "ipBlock": {
                                "cidr": nc_host_ip + "/24"
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

    cmd_add_policy = "echo '{0}' | kubectl create -f -".format(
        json.dumps(kubernetes_policy))
    underlay.sudo_check_call(cmd=cmd_add_policy, host=kube_host_ip)


def kubernetes_allow_traffic_from_agents(underlay, kube_host_ip, namespace):
    # TODO(apanchenko): add network policies using kubernetes API
    label_namespace_cmd = "kubectl label namespace default name=default"
    underlay.sudo_check_call(cmd=label_namespace_cmd, host=kube_host_ip)
    kubernetes_policy = {
        "apiVersion": "extensions/v1beta1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": "access-netchecker-agent",
            "namespace": namespace,
        },
        "spec": {
            "ingress": [
                {
                    "from": [
                        {
                            "namespaceSelector": {
                                "matchLabels": {
                                    "name": namespace
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
            "namespace": namespace,
        },
        "spec": {
            "ingress": [
                {
                    "from": [
                        {
                            "namespaceSelector": {
                                "matchLabels": {
                                    "name": namespace
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

    cmd_add_policy = "echo '{0}' | kubectl create -f -".format(
        json.dumps(kubernetes_policy))
    underlay.sudo_check_call(cmd=cmd_add_policy, host=kube_host_ip)

    cmd_add_policy_hostnet = "echo '{0}' | kubectl create -f -".format(
        json.dumps(kubernetes_policy_hostnet))
    underlay.sudo_check_call(cmd=cmd_add_policy_hostnet, host=kube_host_ip)


@utils.retry(3, requests.exceptions.RequestException)
def get_metric(k8sclient, netchecker_pod_port,
               pod_name='netchecker-server', namespace='default'):

    netchecker_srv_pod_names = [pod.name for pod in
                                k8sclient.pods.list(namespace=namespace)
                                if pod_name in pod.name]

    assert len(netchecker_srv_pod_names) > 0, \
        "No netchecker-server pods found!"
    netchecker_srv_pod = k8sclient.pods.get(name=netchecker_srv_pod_names[0],
                                            namespace=namespace)

    kube_host_ip = netchecker_srv_pod.status.host_ip
    metrics_url = 'http://{0}:{1}/metrics'.format(
        kube_host_ip, netchecker_pod_port)
    response = requests.get(metrics_url, timeout=30)
    LOG.debug('Metrics: [{0}] {1}'.format(
        response.status_code, response.text.strip()))
    return response


def get_service_port(k8sclient, service_name='netchecker',
                     namespace='netchecker'):
    full_service_name = [service.name for service
                         in k8sclient.services.list(namespace=namespace)
                         if service_name in service.name]
    assert len(full_service_name) > 0, "No netchecker service run"

    service_details = k8sclient.services.get(name=full_service_name[0],
                                             namespace=namespace)

    LOG.debug('Necthcecker service details {0}'.format(service_details))
    netchecker_port = service_details.spec.ports[0].node_port
    return netchecker_port
