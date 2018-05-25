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
import time
from uuid import uuid4

import yaml

from devops.helpers import helpers
from devops.error import DevopsCalledProcessError

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests.helpers.utils import retry
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin
from tcp_tests.managers.k8s import cluster
from k8sclient.client.rest import ApiException

LOG = logger.logger


class K8SManager(ExecuteCommandsMixin):
    """docstring for K8SManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        self._api_client = None
        super(K8SManager, self).__init__(
            config=config, underlay=underlay)

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

    @property
    def api(self):
        if self._api_client is None:
            self._api_client = cluster.K8sCluster(
                user=self.__config.k8s_deploy.kubernetes_admin_user,
                password=self.__config.k8s_deploy.kubernetes_admin_password,
                host=self.__config.k8s.kube_host,
                port=self.__config.k8s.kube_apiserver_port,
                default_namespace='default')
        return self._api_client

    @property
    def ctl_host(self):
        nodes = [node for node in self.__config.underlay.ssh if
                 ext.UNDERLAY_NODE_ROLES.k8s_controller in node['roles']]
        return nodes[0]['node_name']

    def get_pod_phase(self, pod_name, namespace=None):
        return self.api.pods.get(
            name=pod_name, namespace=namespace).phase

    def wait_pod_phase(self, pod_name, phase, namespace=None, timeout=60):
        """Wait phase of pod_name from namespace while timeout

        :param str: pod_name
        :param str: namespace
        :param list or str: phase
        :param int: timeout

        :rtype: None
        """
        if isinstance(phase, str):
            phase = [phase]

        def check():
            return self.get_pod_phase(pod_name, namespace) in phase

        helpers.wait(check, timeout=timeout,
                     timeout_msg='Timeout waiting, pod {pod_name} is not in '
                                 '"{phase}" phase'.format(
                                     pod_name=pod_name, phase=phase))

    def wait_pods_phase(self, pods, phase, timeout=60):
        """Wait timeout seconds for phase of pods

        :param pods: list of K8sPod
        :param phase: list or str
        :param timeout: int

        :rtype: None
        """
        if isinstance(phase, str):
            phase = [phase]

        def check(pod_name, namespace):
            return self.get_pod_phase(pod_name, namespace) in phase

        def check_all_pods():
            return all(check(pod.name, pod.metadata.namespace) for pod in pods)

        helpers.wait(
            check_all_pods,
            timeout=timeout,
            timeout_msg='Timeout waiting, pods {0} are not in "{1}" '
                        'phase'.format([pod.name for pod in pods], phase))

    def check_pod_create(self, body, namespace=None, timeout=300, interval=5):
        """Check creating sample pod

        :param k8s_pod: V1Pod
        :param namespace: str
        :rtype: V1Pod
        """
        LOG.info("Creating pod in k8s cluster")
        LOG.debug(
            "POD spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        LOG.debug("Timeout for creation is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        pod = self.api.pods.create(body=body, namespace=namespace)
        pod.wait_running(timeout=300, interval=5)
        LOG.info("Pod '{0}' is created in '{1}' namespace".format(
            pod.name, pod.namespace))
        return self.api.pods.get(name=pod.name, namespace=pod.namespace)

    def wait_pod_deleted(self, podname, timeout=60, interval=5):
        helpers.wait(
            lambda: podname not in [pod.name for pod in self.api.pods.list()],
            timeout=timeout,
            interval=interval,
            timeout_msg="Pod deletion timeout reached!"
        )

    def check_pod_delete(self, k8s_pod, timeout=300, interval=5,
                         namespace=None):
        """Deleting pod from k8s

        :param k8s_pod: tcp_tests.managers.k8s.nodes.K8sNode
        :param k8sclient: tcp_tests.managers.k8s.cluster.K8sCluster
        """
        LOG.info("Deleting pod '{}'".format(k8s_pod.name))
        LOG.debug("Pod status:\n{}".format(k8s_pod.status))
        LOG.debug("Timeout for deletion is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        self.api.pods.delete(body=k8s_pod, name=k8s_pod.name,
                             namespace=namespace)
        self.wait_pod_deleted(k8s_pod.name, timeout, interval)
        LOG.debug("Pod '{}' is deleted".format(k8s_pod.name))

    def check_service_create(self, body, namespace=None):
        """Check creating k8s service

        :param body: dict, service spec
        :param namespace: str
        :rtype: K8sService object
        """
        LOG.info("Creating service in k8s cluster")
        LOG.debug(
            "Service spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        service = self.api.services.create(body=body, namespace=namespace)
        LOG.info("Service '{0}' is created in '{1}' namespace".format(
            service.name, service.namespace))
        return self.api.services.get(name=service.name,
                                     namespace=service.namespace)

    def check_ds_create(self, body, namespace=None):
        """Check creating k8s DaemonSet

        :param body: dict, DaemonSet spec
        :param namespace: str
        :rtype: K8sDaemonSet object
        """
        LOG.info("Creating DaemonSet in k8s cluster")
        LOG.debug(
            "DaemonSet spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        ds = self.api.daemonsets.create(body=body, namespace=namespace)
        LOG.info("DaemonSet '{0}' is created  in '{1}' namespace".format(
            ds.name, ds.namespace))
        return self.api.daemonsets.get(name=ds.name, namespace=ds.namespace)

    def check_ds_ready(self, dsname, namespace=None):
        """Check if k8s DaemonSet is ready

        :param dsname: str, ds name
        :return: bool
        """
        ds = self.api.daemonsets.get(name=dsname, namespace=namespace)
        return (ds.status.current_number_scheduled ==
                ds.status.desired_number_scheduled)

    def wait_ds_ready(self, dsname, namespace=None, timeout=60, interval=5):
        """Wait until all pods are scheduled on nodes

        :param dsname: str, ds name
        :param timeout: int
        :param interval: int
        """
        helpers.wait(
            lambda: self.check_ds_ready(dsname, namespace=namespace),
            timeout=timeout, interval=interval)

    def check_deploy_create(self, body, namespace=None):
        """Check creating k8s Deployment

        :param body: dict, Deployment spec
        :param namespace: str
        :rtype: K8sDeployment object
        """
        LOG.info("Creating Deployment in k8s cluster")
        LOG.debug(
            "Deployment spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        deploy = self.api.deployments.create(body=body, namespace=namespace)
        LOG.info("Deployment '{0}' is created  in '{1}' namespace".format(
            deploy.name, deploy.namespace))
        return self.api.deployments.get(name=deploy.name,
                                        namespace=deploy.namespace)

    def check_deploy_ready(self, deploy_name, namespace=None):
        """Check if k8s Deployment is ready

        :param deploy_name: str, deploy name
        :return: bool
        """
        deploy = self.api.deployments.get(name=deploy_name,
                                          namespace=namespace)
        return deploy.status.available_replicas == deploy.status.replicas

    def wait_deploy_ready(self, deploy_name, namespace=None, timeout=60,
                          interval=5):
        """Wait until all pods are scheduled on nodes

        :param deploy_name: str, deploy name
        :param timeout: int
        :param interval: int
        """
        helpers.wait(
            lambda: self.check_deploy_ready(deploy_name, namespace=namespace),
            timeout=timeout, interval=interval)

    def check_namespace_create(self, name):
        """Check creating k8s Namespace

        :param name: str
        :rtype: K8sNamespace object
        """
        try:
            ns = self.api.namespaces.get(name=name)
            LOG.info("Namespace '{0}' is already exists".format(ns.name))
        except ApiException as e:
            if hasattr(e, "status") and 404 == e.status:
                LOG.info("Creating Namespace in k8s cluster")
                ns = self.api.namespaces.create(
                    body={'metadata': {'name': name}})
                LOG.info("Namespace '{0}' is created".format(ns.name))
                # wait 10 seconds until a token for new service account
                # is created
                time.sleep(10)
                ns = self.api.namespaces.get(name=ns.name)
            else:
                raise
        return ns

    def create_objects(self, path):
        if isinstance(path, str):
            path = [path]
        params = ' '.join(["-f {}".format(p) for p in path])
        cmd = 'kubectl create {params}'.format(params=params)
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            LOG.info("Running command '{cmd}' on node {node}".format(
                cmd=cmd,
                node=remote.hostname)
            )
            result = remote.check_call(cmd)
            LOG.info(result['stdout'])

    def get_running_pods(self, pod_name, namespace=None):
        pods = [pod for pod in self.api.pods.list(namespace=namespace)
                if (pod_name in pod.name and pod.status.phase == 'Running')]
        return pods

    def get_pods_number(self, pod_name, namespace=None):
        pods = self.get_running_pods(pod_name, namespace)
        return len(pods)

    def get_running_pods_by_ssh(self, pod_name, namespace=None):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call("kubectl get pods --namespace {} |"
                                       " grep {} | awk '{{print $1 \" \""
                                       " $3}}'".format(namespace,
                                                       pod_name))['stdout']
            running_pods = [data.strip().split()[0] for data in result
                            if data.strip().split()[1] == 'Running']
            return running_pods

    def get_pods_restarts(self, pod_name, namespace=None):
        pods = [pod.status.container_statuses[0].restart_count
                for pod in self.get_running_pods(pod_name, namespace)]
        return sum(pods)

    def run_conformance(self, timeout=60 * 60):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call(
                "set -o pipefail; docker run --net=host -e API_SERVER="
                "'http://127.0.0.1:8080' {} | tee k8s_conformance.log".format(
                    self.__config.k8s.k8s_conformance_image),
                timeout=timeout)['stdout']
            return result

    def get_k8s_masters(self):
        k8s_masters_fqdn = self._salt.get_pillar(tgt='I@kubernetes:master',
                                                 pillar='linux:network:fqdn')
        return [self._K8SManager__underlay.host_by_node_name(node_name=v)
                for pillar in k8s_masters_fqdn for k, v in pillar.items()]

    def kubectl_run(self, name, image, port):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call(
                "kubectl run {0} --image={1} --port={2}".format(
                    name, image, port
                )
            )
            return result

    def kubectl_expose(self, resource, name, port, type):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call(
                "kubectl expose {0} {1} --port={2} --type={3}".format(
                    resource, name, port, type
                )
            )
            return result

    def kubectl_annotate(self, resource, name, annotation):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call(
                "kubectl annotate {0} {1} {2}".format(
                    resource, name, annotation
                )
            )
            return result

    def get_svc_ip(self, name, namespace='kube-system'):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call(
                "kubectl get svc {0} -n {1} | "
                "awk '{{print $2}}' | tail -1".format(name, namespace)
            )
            return result['stdout'][0].strip()

    @retry(300, exception=DevopsCalledProcessError)
    def nslookup(self, host, src):
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            remote.check_call("nslookup {0} {1}".format(host, src))

# ---------------------------- Virtlet methods -------------------------------
    def install_jq(self):
        """Install JQuery on node. Required for changing yamls on the fly.

        :return:
        """
        cmd = "apt install jq -y"
        return self.__underlay.check_call(cmd, node_name=self.ctl_host)

    def git_clone(self, project, target):
        cmd = "git clone {0} {1}".format(project, target)
        return self.__underlay.check_call(cmd, node_name=self.ctl_host)

    def run_vm(self, name=None, yaml_path='~/virtlet/examples/cirros-vm.yaml'):
        if not name:
            name = 'virtlet-vm-{}'.format(uuid4())
        cmd = (
            "kubectl convert -f {0} --local "
            "-o json | jq '.metadata.name|=\"{1}\"' | kubectl create -f -")
        self.__underlay.check_call(cmd.format(yaml_path, name),
                                   node_name=self.ctl_host)
        return name

    def get_vm_info(self, name, jsonpath="{.status.phase}", expected=None):
        cmd = "kubectl get po {} -n default".format(name)
        if jsonpath:
            cmd += " -o jsonpath={}".format(jsonpath)
        return self.__underlay.check_call(
            cmd, node_name=self.ctl_host, expected=expected)

    def wait_active_state(self, name, timeout=180):
        helpers.wait(
            lambda: self.get_vm_info(name)['stdout'][0] == 'Running',
            timeout=timeout,
            timeout_msg="VM {} didn't Running state in {} sec. "
                        "Current state: ".format(
                name, timeout, self.get_vm_info(name)['stdout'][0]))

    def delete_vm(self, name, timeout=180):
        cmd = "kubectl delete po -n default {}".format(name)
        self.__underlay.check_call(cmd, node_name=self.ctl_host)

        helpers.wait(
            lambda:
            "Error from server (NotFound):" in
            " ".join(self.get_vm_info(name, expected=[0, 1])['stderr']),
            timeout=timeout,
            timeout_msg="VM {} didn't Running state in {} sec. "
                        "Current state: ".format(
                name, timeout, self.get_vm_info(name)['stdout'][0]))

    def adjust_cirros_resources(
            self, cpu=2, memory='256',
            target_yaml='virtlet/examples/cirros-vm-exp.yaml'):
        # We will need to change params in case of example change
        cmd = ("cd ~/virtlet/examples && "
               "cp cirros-vm.yaml {2} && "
               "sed -r 's/^(\s*)(VirtletVCPUCount\s*:\s*\"1\"\s*$)/ "
               "\1VirtletVCPUCount: \"{0}\"/' {2} && "
               "sed -r 's/^(\s*)(memory\s*:\s*128Mi\s*$)/\1memory: "
               "{1}Mi/' {2}".format(cpu, memory, target_yaml))
        self.__underlay.check_call(cmd, node_name=self.ctl_host)

    def get_domain_name(self, vm_name):
        cmd = ("~/virtlet/examples/virsh.sh list --name | "
               "grep -i {0} ".format(vm_name))
        result = self.__underlay.check_call(cmd, node_name=self.ctl_host)
        return result['stdout'].strip()

    def get_vm_cpu_count(self, domain_name):
        cmd = ("~/virtlet/examples/virsh.sh dumpxml {0} | "
               "grep 'cpu' | grep -o '[[:digit:]]*'".format(domain_name))
        result = self.__underlay.check_call(cmd, node_name=self.ctl_host)
        return int(result['stdout'].strip())

    def get_vm_memory_count(self, domain_name):
        cmd = ("~/virtlet/examples/virsh.sh dumpxml {0} | "
               "grep 'memory unit' | "
               "grep -o '[[:digit:]]*'".format(domain_name))
        result = self.__underlay.check_call(cmd, node_name=self.ctl_host)
        return int(result['stdout'].strip())

    def get_domain_id(self, domain_name):
        cmd = ("virsh dumpxml {} | grep id=\' | "
               "grep -o [[:digit:]]*".format(domain_name))
        result = self.__underlay.check_call(cmd, node_name=self.ctl_host)
        return int(result['stdout'].strip())

    def list_vm_volumes(self, domain_name):
        domain_id = self.get_domain_id(domain_name)
        cmd = ("~/virtlet/examples/virsh.sh domblklist {} | "
               "tail -n +3 | awk {{'print $2'}}".format(domain_id))
        result = self.__underlay.check_call(cmd, node_name=self.ctl_host)
        return result['stdout'].strip()

    def run_virtlet_conformance(self, timeout=60 * 120,
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
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            result = remote.check_call(cmd, timeout=timeout)
            stderr = result['stderr']
            stdout = result['stdout']
            LOG.info("Test results stdout: {}".format(stdout))
            LOG.info("Test results stderr: {}".format(stderr))
        return result

    def start_k8s_cncf_verification(self, timeout=60 * 90):
        cncf_cmd = ("curl -L https://raw.githubusercontent.com/cncf/"
                    "k8s-conformance/master/sonobuoy-conformance.yaml"
                    " | kubectl apply -f -")
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
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
                             file_path='report.xml', **kwargs):
        """
        Download file from docker or k8s container to node

        :param system: docker or k8s
        :param container: Full name of part of name
        :param file_path: File path in container
        :param kwargs: Used to control pod and namespace
        :return:
        """
        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
            if system is 'docker':
                cmd = ("docker ps --all | grep {0} |"
                       " awk '{{print $1}}'".format(container))
                result = remote.check_call(cmd, raise_on_err=False)
                if result['stdout']:
                    container_id = result['stdout'][0].strip()
                else:
                    LOG.info('No container found, skipping extraction...')
                    return
                cmd = "docker start {}".format(container_id)
                remote.check_call(cmd, raise_on_err=False)
                cmd = "docker cp {0}:/{1} .".format(container_id, file_path)
                remote.check_call(cmd, raise_on_err=False)
            else:
                # system is k8s
                pod_name = kwargs.get('pod_name')
                pod_namespace = kwargs.get('pod_namespace')
                cmd = 'kubectl cp {0}/{1}:/{2} .'.format(
                    pod_namespace, pod_name, file_path)
                remote.check_call(cmd, raise_on_err=False)

    def download_k8s_logs(self, files):
        """
        Download JUnit report and conformance logs from cluster
        :param files:
        :return:
        """
        master_host = self.__config.salt.salt_master_host
        with self.__underlay.remote(host=master_host) as r:
            for log_file in files:
                cmd = "rsync -r {0}:/root/{1} /root/".format(self.ctl_host,
                                                             log_file)
                r.check_call(cmd, raise_on_err=False)
                LOG.info("Downloading the artifact {0}".format(log_file))
                r.download(destination=log_file, target=os.getcwd())

    def combine_xunit(self, path, output):
        """
        Function to combine multiple xmls with test results to
        one.

        :param path: Path where xmls to combine located
        :param output: Path to xml file where output will stored
        :return:
        """
        with self.__underlay.remote(node_name=self.ctl_host) as r:
            cmd = ("apt-get install python-setuptools -y; "
                   "pip install git+https://github.com/mogaika/xunitmerge.git")
            LOG.debug('Installing xunitmerge')
            r.check_call(cmd, raise_on_err=False)
            LOG.debug('Merging xunit')
            cmd = ("cd {0}; arg = ''; "
                   "for i in $(ls | grep xml); "
                   "do arg=\"$arg $i\"; done && "
                   "xunitmerge $arg {1}".format(path, output))
            r.check_call(cmd, raise_on_err=False)

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

        with self.__underlay.remote(
                node_name=self.ctl_host) as remote:
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
