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

import os
import six
import requests
import yaml

import kubernetes
from kubernetes import client

from devops.helpers import helpers
from devops.error import DevopsCalledProcessError

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests.helpers.utils import retry
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin

LOG = logger.logger
DEFAULT_NAMESPACE = 'default'
STATUS_RUNNING = 'Running'


class K8SManager(ExecuteCommandsMixin):
    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        self._api_core_client = None
        self._api_apps_client = None
        self._api_extensions_client = None
        super(K8SManager, self).__init__(config=config, underlay=underlay)

    def install(self, commands):
        self.execute_commands(commands,
                              label='Install Kubernetes services')
        self.__config.k8s.k8s_installed = True
        self.__config.k8s.kube_host = self.get_proxy_api()

    def get_proxy_api(self):
        k8s_proxy_ip_pillars = self._salt.get_pillar(
            tgt='I@haproxy:proxy:enabled:true and I@kubernetes:master',
            pillar='haproxy:proxy:listen:k8s_secure:binds:address')
        k8s_hosts = self._salt.get_pillar(
            tgt='I@haproxy:proxy:enabled:true and I@kubernetes:master',
            pillar='kubernetes:pool:apiserver:host')
        k8s_proxy_ip = set([ip
                            for item in k8s_proxy_ip_pillars
                            for node, ip in item.items() if ip])
        k8s_hosts = set([ip
                         for item in k8s_hosts
                         for node, ip in item.items() if ip])
        assert len(k8s_hosts) == 1, (
            "Found more than one Kubernetes API hosts in pillars:{0}, "
            "expected one!").format(k8s_hosts)
        k8s_host = k8s_hosts.pop()
        assert k8s_host in k8s_proxy_ip, (
            "Kubernetes API host:{0} not found in proxies:{} "
            "on k8s master nodes. K8s proxies are expected on "
            "nodes with K8s master").format(k8s_host, k8s_proxy_ip)
        return k8s_host

    def _api_init(self):
        with self.__underlay.remote(host=self.ctl_host) as r:
            r.download(destination="/etc/kubernetes/admin-kube-config",
                       target=os.path.join(os.getcwd(), "kubeconfig"))
        kubernetes.config.load_kube_config('kubeconfig')
        self._api_core_client = client.CoreV1Api()
        self._api_apps_client = client.AppsV1Api()
        self._api_extensions_client = client.ExtensionsV1beta1Api()

    @property
    def api(self):
        """
            :rtype: client.apis.core_v1_api.CoreV1Api
        """
        if self._api_core_client is None:
            self._api_init()
        return self._api_core_client

    @property
    def api_apps(self):
        """
            :rtype: client.apis.apps_v1_api.AppsV1Api
        """
        if self._api_apps_client is None:
            self._api_init()
        return self._api_core_client

    @property
    def api_extensions(self):
        """
            :rtype: client.apis.extensions_v1beta1_api.ExtensionsV1beta1Api
        """
        if self._api_extensions_client is None:
            self._api_init()
        return self._api_extensions_client

    def get_controllers(self):
        """ Return list of controllers ssh underlays """
        return [node for node in self.__config.underlay.ssh if
                ext.UNDERLAY_NODE_ROLES.k8s_controller in node['roles']]

    def get_masters(self):
        """ Return list of kubernetes masters hosts"""
        masters_fqdn = self._salt.get_pillar(
            tgt='I@kubernetes:master', pillar='linux:network:fqdn')
        return [self.__underlay.host_by_node_name(node_name=v)
                for pillar in masters_fqdn for k, v in pillar.items()]

    @property
    def controller_name(self):
        """ Return node name of controller node that used for all actions """
        names = [node['node_name'] for node in self.get_controllers()]
        # we want to return same controller name every time
        return names.sort()[0]

    def pod(self, namespace=DEFAULT_NAMESPACE, name=None):
        return K8SPod(self, namespace, name)

    def service(self, namespace=DEFAULT_NAMESPACE, name=None):
        return K8SService(self, namespace, name)

    def deployment(self, namespace=DEFAULT_NAMESPACE, name=None):
        return K8SDeployment(self, namespace, name)

    def daemon_set(self, namespace=DEFAULT_NAMESPACE, name=None):
        return K8SDaemonSet(self, namespace, name)

    def namespace(self, name=None):
        return K8SNamespace(self, name)

    def node(self, name=None):
        return K8SNode(self, name)

    def list_pods(self, namespace=None, prefix=None, phases=None):
        pods = self.api.list_pod_for_all_namespaces().items
        if namespace is not None:
            pods = [pod for pod in pods if pod.metadata.namespace == namespace]

        if phases is not None:
            if isinstance(phases, six.string_types):
                phases = [phases]
            pods = [pod for pod in pods if pod.status.phase in phases]

        names = [pod.metadata.name for pod in pods]
        if prefix is not None:
            names = [name for name in names if name.startswith(prefix)]

        return names

    def list_services(self, namespace=None, prefix=None):
        services = self.api.list_service_for_all_namespaces().items
        if namespace is not None:
            services = [svc for svc in services if
                        svc.metadata.namespace == namespace]

        names = [svc.metadata.name for svc in services]
        if prefix is not None:
            names = [name for name in names if name.startswith(prefix)]

        return names

    def list_nodes(self):
        return [node.metadata.name for node in self.api.list_node().items]

    def controller_check_call(self, cmd, **kwargs):
        return self.__underlay.check_call(
            cmd=cmd, node_name=self.controller_name, **kwargs)

    @property
    def kubectl(self):
        return K8SKubectl(self)

    def run_conformance(self, timeout=60*60, log_out='k8s_conformance.log',
                        raise_on_err=True, node_name=None,
                        api_server='http://127.0.0.1:8080'):
        if node_name is None:
            node_name = self.controller_name
        cmd = "set -o pipefail; docker run --net=host " \
              "-e API_SERVER='{api}' {image} | tee '{log}'".format(
               api=api_server, log=log_out,
               image=self.__config.k8s.k8s_conformance_image)
        return self.__underlay.check_call(
               cmd=cmd, node_name=node_name, timeout=timeout,
               raise_on_err=raise_on_err)

    @retry(50, exception=DevopsCalledProcessError)
    def nslookup(self, host, src):
        self.controller_check_call("nslookup {0} {1}".format(host, src))

    @retry(50, exception=DevopsCalledProcessError)
    def curl(self, url):
        """
        Run curl on controller and return stdout

        :param url: url to curl
        :return: response string
        """
        result = self.controller_check_call("curl -s -S \"{}\"".format(url))
        LOG.debug("curl \"{0}\" result: {1}".format(url, result['stdout']))
        return result['stdout']

    def run_virtlet_conformance(self, timeout=60*60*2,
                                log_file='virtlet_conformance.log'):
        if self.__config.k8s.run_extended_virtlet_conformance:
            ci_image = "cloud-images.ubuntu.com/xenial/current/" \
                       "xenial-server-cloudimg-amd64-disk1.img"
            cmd = ("set -o pipefail; "
                   "docker run --net=host {0} /virtlet-e2e-tests "
                   "-include-cloud-init-tests -junitOutput report.xml "
                   "-image {2} -sshuser ubuntu -memoryLimit 1024 "
                   "-alsologtostderr -cluster-url http://127.0.0.1:8080 "
                   "-ginkgo.focus '\[Conformance\]' "
                   "| tee {1}".format(
                    self.__config.k8s_deploy.kubernetes_virtlet_image,
                    log_file, ci_image))
        else:
            cmd = ("set -o pipefail; "
                   "docker run --net=host {0} /virtlet-e2e-tests "
                   "-junitOutput report.xml "
                   "-alsologtostderr -cluster-url http://127.0.0.1:8080 "
                   "-ginkgo.focus '\[Conformance\]' "
                   "| tee {1}".format(
                    self.__config.k8s_deploy.kubernetes_virtlet_image,
                    log_file))
        LOG.info("Executing: {}".format(cmd))
        with self.__underlay.remote(node_name=self.controller_name) as remote:
            result = remote.check_call(cmd, timeout=timeout)
            LOG.info("Test results stdout: {}".format(result['stdout']))
            LOG.info("Test results stderr: {}".format(result['stderr']))
        return result

    def start_k8s_cncf_verification(self, timeout=60*90):
        # TODO: rewrite due to
        # https://github.com/cncf/k8s-conformance/commit/354cbca920af23e60c95546ea0d076748047385c
        cncf_cmd = ("curl -L https://raw.githubusercontent.com/cncf/"
                    "k8s-conformance/master/sonobuoy-conformance.yaml"
                    " | kubectl apply -f -")
        with self.__underlay.remote(node_name=self.controller_name) as remote:
            remote.check_call(cncf_cmd, timeout=60)
            self.wait_pod_phase('sonobuoy', 'Running',
                                namespace='sonobuoy', timeout=120)

            wait_cmd = ('kubectl logs -n sonobuoy sonobuoy | '
                        'grep "sonobuoy is now blocking"')

            expected = [0, 1]
            helpers.wait(
                lambda: remote.check_call(
                    wait_cmd, expected=expected).exit_code == 0,
                interval=30, timeout=timeout,
                timeout_msg="Timeout for CNCF reached."
            )

    def extract_file_to_node(self, system='docker',
                             container='virtlet',
                             file_path='report.xml',
                             out_dir='.',
                             **kwargs):
        """
        Download file from docker or k8s container to node

        :param system: docker or k8s
        :param container: Full name of part of name
        :param file_path: File path in container
        :param kwargs: Used to control pod and namespace
        :param out_dir: Output directory
        :return:
        """
        with self.__underlay.remote(node_name=self.controller_name) as remote:
            if system is 'docker':
                cmd = ("docker ps --all | grep \"{0}\" |"
                       " awk '{{print $1}}'".format(container))
                result = remote.check_call(cmd, raise_on_err=False)
                if result['stdout']:
                    container_id = result['stdout'][0].strip()
                else:
                    LOG.info('No container found, skipping extraction...')
                    return
                cmd = "docker start {}".format(container_id)
                remote.check_call(cmd, raise_on_err=False)
                cmd = "docker cp \"{0}:/{1}\" \"{2}\"".format(
                    container_id, file_path, out_dir)
                remote.check_call(cmd, raise_on_err=False)
            else:  # system is k8s
                pod_name = kwargs.get('pod_name')
                pod_namespace = kwargs.get('pod_namespace')
                cmd = 'kubectl cp \"{0}/{1}:/{2}\" \"{3}\"'.format(
                    pod_namespace, pod_name, file_path, out_dir)
                remote.check_call(cmd, raise_on_err=False)

    def download_from_controller(self, files):
        """
        Download files from controller that used to run tests
        :param files:
        :return:
        """
        with self.__underlay.remote(host=self.controller_name) as r:
            for f in files:
                LOG.info("Downloading file {0}".format(f))
                r.download(destination=f, target=os.getcwd())

    def combine_xunit(self, path, output):
        """
        Function to combine multiple xmls with test results to
        one.

        :param path: Path where xmls to combine located
        :param output: Path to xml file where output will stored
        :return:
        """
        cmd = ("apt-get install python-setuptools -y; "
               "pip install "
               "https://github.com/mogaika/xunitmerge/archive/master.zip")
        LOG.debug('Installing xunitmerge')
        self.controller_check_call(cmd, raise_on_err=False)

        cmd = ("cd {0}; arg = ''; "
               "for i in $(ls | grep xml); "
               "do arg=\"$arg $i\"; done && "
               "xunitmerge $arg {1}".format(path, output))
        LOG.debug('Merging xunit')
        self.controller_check_call(cmd)

    def manage_cncf_archive(self):
        """
        Function to untar archive, move files, that we are needs to the
        home folder, prepare it to downloading and clean the trash.
        Will generate files: e2e.log, junit_01.xml, cncf_results.tar.gz
        and version.txt
        :return:
        """

        # Namespace and pod name may be hardcoded since this function is
        # very specific for cncf and cncf is not going to change
        # those launch pod name and namespace.
        get_tar_name_cmd = ("kubectl logs -n sonobuoy sonobuoy | "
                            "grep 'Results available' | "
                            "sed 's/.*\///' | tr -d '\"'")

        with self.__underlay.remote(node_name=self.controller_name) as remote:
            tar_name = remote.check_call(get_tar_name_cmd)['stdout'][0].strip()
            untar = "mkdir result && tar -C result -xzf {0}".format(tar_name)
            remote.check_call(untar, raise_on_err=False)
            manage_results = ("mv result/plugins/e2e/results/e2e.log . && "
                              "mv result/plugins/e2e/results/junit_01.xml . ;"
                              "kubectl version > version.txt")
            remote.check_call(manage_results, raise_on_err=False)
            cleanup_host = "rm -rf result"
            remote.check_call(cleanup_host, raise_on_err=False)
            # This one needed to use download fixture, since I don't know
            # how possible apply fixture arg dynamically from test.
            rename_tar = "mv {0} cncf_results.tar.gz".format(tar_name)
            remote.check_call(rename_tar, raise_on_err=False)

    def update_k8s_version(self, tag):
        """
        Update k8s images tag version in cluster meta and apply required
        for update states

        :param tag: New version tag of k8s images
        :return:
        """
        master_host = self.__config.salt.salt_master_host

        def update_image_tag_meta(config, image_name):
            image_old = config.get(image_name)
            image_base = image_old.split(':')[0]
            image_new = "{}:{}".format(image_base, tag)
            LOG.info("Changing k8s '{0}' image cluster meta to '{1}'".format(
                image_name, image_new))

            with self.__underlay.remote(host=master_host) as r:
                cmd = "salt-call reclass.cluster_meta_set" \
                      " name={0} value={1}".format(image_name, image_new)
                r.check_call(cmd)
            return image_new

        cfg = self.__config

        update_image_tag_meta(cfg.k8s_deploy, "kubernetes_hyperkube_image")
        update_image_tag_meta(cfg.k8s_deploy, "kubernetes_pause_image")
        cfg.k8s.k8s_conformance_image =\
            update_image_tag_meta(cfg.k8s, "k8s_conformance_image")

        update_commands = self.__underlay.read_template(
            cfg.k8s_deploy.k8s_update_steps_path)
        self.execute_commands(
            update_commands,
            label="Updating kubernetes cluster to '{}' version".format(tag))

    def get_keepalived_vip(self):
        """
        :return: IP address
        :rtype: str
        """
        ctl_vip_pillar = self._salt.get_pillar(
            tgt="I@kubernetes:control:enabled:True",
            pillar="_param:cluster_vip_address")[0]
        return ctl_vip_pillar.values()[0]

    def get_sample_deployment(self, name, **kwargs):
        return K8SSampleDeployment(self, name, **kwargs)

    def get_runned_pods_count(self, namespace, prefix):
        return len(self.list_pods(namespace=namespace, prefix=prefix,
                                  phases=STATUS_RUNNING))


class K8SKubectl:
    def __init__(self, manager):
        self._manager = manager

    def run(self, namespace, name, image, port, replicas=1):
        cmd = "kubectl -n {0} run {1} --image={2} --port={3} --replicas={4}".\
            format(namespace, name, image, port, replicas)
        return self._manager.controller_check_call(cmd)

    def expose(self, namespace, resource_type, resource_name, port,
               service_name, service_type='ClusterIP'):
        cmd = "kubectl -n {0} expose {1} {2} --port={3} --type={4}".format(
            namespace, resource_type, resource_name, port, service_type)
        if service_name is not None:
            cmd += " --name={}".format(service_name)
        return self._manager.controller_check_call(cmd)

    def execute(self, namespace, pod_name, cmd):
        cmd = "kubectl -m {0} exec {1} -- {2}".format(
            namespace, pod_name, cmd)
        return self._manager.controller_check_call(cmd)


class K8SNamedResource:
    def __init__(self, manager, namespace=DEFAULT_NAMESPACE, name=None):
        self._manager = manager
        self._namespace = namespace
        self._name = name

    def name(self):
        return self._name

    def _yaml_body_file_parse(self, body=None, file_path=None):
        if file_path is not None:
            with open(file_path) as f:
                return yaml.safe_load(f)
        elif isinstance(body, six.string_types):
            return yaml.safe_load(body)
        elif body is None:
            raise ValueError("Provide body or file_path argument")
        if self._name is not None:
            body['metadata']['name'] = self._name


class K8SPod(K8SNamedResource):
    def __init__(self, manager, namespace=DEFAULT_NAMESPACE, name=None):
        super(K8SPod, self).__init__(manager, namespace, name)

    def create(self, body=None, file_path=None):
        body = self._yaml_body_file_parse(body, file_path)

        LOG.debug("Pod spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False)))

        pod = self.manager.api.create_namespaced_pod(self._namespace, body)

        LOG.info("Pod '{0}' is created in '{1}' namespace".format(
            pod.metadata.name, pod.metadata.namespace))

        self._name = pod.metadata.name
        return self

    def read(self):
        return \
            self._manager.api.read_namespaced_pod(self.name, self._namespace)

    def get_phase(self):
        return self.read().status.phase

    def wait_phase(self, phases, timeout=120, interval=3):
        if isinstance(phases, str):
            phases = [phases]

        helpers.wait(lambda: self.get_phase() in phases,
                     timeout=timeout, interval=interval,
                     timeout_msg='Timeout waiting, pod {0} phase is not in '
                                 '"{1}"'.format(self.name, phases))
        return self

    def wait_running(self, timeout=300):
        return self.wait_phase('Running', timeout=timeout)

    def patch(self, body):
        self._manager.patch_namespaced_pod(self._name, self._namespace, body)

    def get_ips_from_inside(self, exclude_local=True):
        result = self._manager.kubectl.execute(
            self._namespace, self._name,
            "ip a|grep 'inet '|awk '{{print $2}}'")

        ips = [line.strip().split('/')[0] for line in result['stdout']]
        if exclude_local:
            ips = [ip for ip in ips if not ip.startswith("127.")]
        return ips


class K8SService(K8SNamedResource):
    def __init__(self, manager, namespace=DEFAULT_NAMESPACE, name=None):
        super(K8SService, self).__init__(manager, namespace, name)

    def create(self, body=None, file_path=None):
        body = self._yaml_body_file_parse(body, file_path)

        LOG.debug("Service spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False)))

        svc = self.manager.api.create_namespaced_service(self._namespace, body)

        LOG.info("Service '{0}' is created in '{1}' namespace".format(
            svc.metadata.name, svc.metadata.namespace))

        self._name = svc.metadata.name
        return self

    def read(self):
        return \
            self._manager.api.read_namespaced_pod(self.name, self._namespace)

    def get_ip(self, external=False):
        if external:
            return self.read().status.loadBalancer.ingress.ip
        else:
            return self.read().spec.clusterIP


class K8SDaemonSet(K8SNamedResource):
    def __init__(self, manager, namespace=DEFAULT_NAMESPACE, name=None):
        super(K8SDaemonSet, self).__init__(manager, namespace, name)

    def create(self, body=None, file_path=None):
        body = self._yaml_body_file_parse(body, file_path)

        LOG.debug("DaemonSet spec to create:\n{}".format(
            yaml.dump(body, default_flow_style=False)))

        ds = self.api_apps.create_namespaced_daemon_set(self._namespace, body)

        LOG.info("DaemonSet '{0}' is created  in '{1}' namespace".format(
            ds.metadata.name, ds.metadata.namespace))

        self._name = ds.metadata.name
        return self

    def read(self):
        return self.api_apps.read_namespaced_daemon_set(
            self._name, self._namespace)

    def is_ready(self):
        ds = self.read()
        return (ds.status.current_number_scheduled ==
                ds.status.desired_number_scheduled)

    def wait_ready(self, timeout=60, interval=5):
        helpers.wait(lambda: self.is_ready(),
                     timeout=timeout, interval=interval)
        return self


class K8SDeployment(K8SNamedResource):
    def __init__(self, manager, namespace=DEFAULT_NAMESPACE, name=None):
        super(K8SDeployment, self).__init__(manager, namespace, name)

    def create(self, body=None, file_path=None):
        body = self._yaml_body_file_parse(body, file_path)

        LOG.debug("Deployment spec to create:\n{}".format(
            yaml.dump(body, default_flow_style=False)))

        dep = self.api.create_namespaced_deployment(self._namespace, body)

        LOG.info("Deployment '{0}' is created  in '{1}' namespace".format(
            dep.metadata.name, dep.metadata.namespace))

        self._name = dep.metadata.name
        return self

    def read(self):
        return self.api.read_namespaced_deployment(self._name, self._namespace)

    def is_ready(self):
        dep = self.read()
        return dep.status.available_replicas == dep.status.replicas

    def wait_ready(self, timeout=60, interval=5):
        helpers.wait(lambda: self.is_ready(),
                     timeout=timeout, interval=interval)
        return self

    def expose(self, port, service_name, service_type='ClusterIP'):
        self._manager.kubectl.expose(
            self._namespace, 'deployment', self._name, port,
            service_name, service_type=service_type)
        return self._manager.service(self._namespace, service_name)


class K8SNamespace(K8SNamedResource):
    def __init__(self, manager, name=None):
        super(K8SNamespace, self).__init__(manager, None, name)

    def read(self):
        return self.api.read_namespace(self._name)

    def patch(self, body):
        self.api.patch_namespace(self._name, body)


class K8SNode(K8SNamedResource):
    def __init__(self, manager, name=None):
        super(K8SNode, self).__init__(manager, None, name)

    def read(self):
        return self.api.read_node(self._name)


class K8SSampleDeployment:
    def __init__(self, manager, name,
                 namespace=DEFAULT_NAMESPACE,
                 image='gcr.io/google-samples/node-hello:1.0',
                 port=8080,
                 replicas=2):
        manager.kubectl.run(name, image=image, port=port, replicas=replicas)

        self._manager = manager
        self._port = port
        self._index = 1  # used to generate svc name
        self._deployment = manager.deployment(name=name, namespace=namespace)
        self._svc = None

    def wait_ready(self):
        self._deployment.wait_ready()
        return self

    def svc(self):
        """ Return last exposed service"""
        return self._svc

    def expose(self, service_type='ClusterIP'):
        service_name = "svc_{0}_{1}".format(self._name, self._index)
        self._svc = self._deployment.expose(
            self._port, service_name=service_name, service_type=service_type)
        return self._svc

    def curl(self, svc=None, external=False):
        if svc is None:
            svc = self.svc()
        url = "http://{0}:{1}".format(svc.get_ip(external=external), self.port)
        if external:
            return requests.get(url).text
        else:
            return self.manager.curl(url)

    def is_service_available(self, svc, external=False):
        return "Hello Kubernetes!" in self.curl(svc, external=external)
