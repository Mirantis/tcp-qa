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
import requests
import yaml

from devops.helpers import helpers
from devops.error import DevopsCalledProcessError

from tcp_tests import logger
from tcp_tests.helpers import ext
from tcp_tests.helpers.utils import retry
from tcp_tests.managers.execute_commands import ExecuteCommandsMixin
from tcp_tests.managers.k8s import cluster

LOG = logger.logger


class K8SManager(ExecuteCommandsMixin):
    """docstring for K8SManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, salt):
        self.__config = config
        self.__underlay = underlay
        self._salt = salt
        self._api = None
        self._controller_name = None
        self.kubectl = K8SKubectlCli(self)
        self.virtlet = K8SVirtlet(self)
        self.conformance_node = None
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
        ca_result = self.controller_check_call(
            'base64 --wrap=0 /etc/kubernetes/ssl/ca-kubernetes.crt')

        self._api = cluster.K8sCluster(
            user=self.__config.k8s_deploy.kubernetes_admin_user,
            password=self.__config.k8s_deploy.kubernetes_admin_password,
            ca=ca_result['stdout'][0],
            host=self.__config.k8s.kube_host,
            port=self.__config.k8s.kube_apiserver_port)

    @property
    def api(self):
        """
            :rtype: cluster.K8sCluster
        """
        if self._api is None:
            self._api_init()
        return self._api

    def get_controllers(self):
        """ Return list of controllers ssh underlays """
        return [node for node in self.__config.underlay.ssh if
                ext.UNDERLAY_NODE_ROLES.k8s_controller in node['roles']]

    def get_masters(self):
        """ Return list of kubernetes masters hosts fqdn """
        masters_fqdn = self._salt.get_pillar(
            tgt='I@kubernetes:master', pillar='linux:network:fqdn')
        return [self.__underlay.host_by_node_name(node_name=v)
                for pillar in masters_fqdn for k, v in pillar.items()]

    def renew_controller(self, controller_node_name=None):
        """ Changes controller returned by controller_name property """
        if controller_node_name is not None:
            self._controller_name = controller_node_name
            return self._controller_name
        names = [node['node_name'] for node in self.get_controllers()]
        if len(names) == 1 and names[0] == self._controller_name:
            LOG.warn(
                "Cannot change controller because there is only 1 of them")
            return
        else:
            for name in names:
                if name != self._controller_name:
                    self._controller_name = name
                    return

    @property
    def controller_name(self):
        """ Return node name of controller node that used for all actions """
        if self._controller_name is None:
            self.renew_controller()
        return self._controller_name

    @property
    def controller_minion_id(self):
        """ Return node name of controller node that used for all actions """
        minion_ids = [minion_id['minion_id'] for minion_id in
                      self.get_controllers()]
        # we want to return same controller name every time
        minion_ids.sort()
        return minion_ids[0]

    @property
    def is_metallb_enabled(self):
        ctl_tgt = self.controller_minion_id
        LOG.debug("Controller target: {}".format(ctl_tgt))

        result = self._salt.get_pillar(
            tgt=ctl_tgt,
            pillar='kubernetes:common:addons:metallb:enabled')
        metallb = result[0].get(ctl_tgt, False)
        LOG.info("{} kubernetes:common:addons:metallb:enabled: {}"
                 .format(ctl_tgt, bool(metallb)))
        return metallb

    @property
    def is_ingress_nginx_enabled(self):
        ctl_tgt = self.controller_minion_id
        LOG.debug("Controller target: {}".format(ctl_tgt))

        result = self._salt.get_pillar(
            tgt=ctl_tgt,
            pillar='kubernetes:common:addons:ingress-nginx:enabled')
        ingress_nginx = result[0].get(ctl_tgt, False)
        LOG.info("{} kubernetes:common:addons:ingress-nginx:enabled: {}"
                 .format(ctl_tgt, bool(ingress_nginx)))
        return ingress_nginx

    def controller_check_call(self, cmd, **kwargs):
        """ Run command on controller and return result """
        LOG.info("running cmd on k8s controller: {}".format(cmd))
        return self.__underlay.check_call(
            cmd=cmd, node_name=self.controller_name, **kwargs)

    def get_keepalived_vip(self):
        """
        Return k8s VIP IP address

        :return: str, IP address
        """
        ctl_vip_pillar = self._salt.get_pillar(
            tgt="I@kubernetes:control",
            pillar="_param:cluster_vip_address")[0]
        return ctl_vip_pillar.values()[0]

    def run_sample_deployment(self, name, **kwargs):
        return K8SSampleDeployment(self, name, **kwargs)

    def get_pod_ips_from_container(self, pod_name, exclude_local=True,
                                   namespace='default'):
        """ Get ips from container using 'ip a'
            Required for cni-genie multi-cni cases

            :return: list of IP adresses
        """
        cmd = "ip a|grep \"inet \"|awk '{{print $2}}'"
        result = self.kubectl.cli_exec(namespace, pod_name, cmd)['stdout']
        ips = [line.strip().split('/')[0] for line in result]
        if exclude_local:
            ips = [ip for ip in ips if not ip.startswith("127.")]
        return ips

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
        cfg.k8s.k8s_conformance_image = update_image_tag_meta(
            cfg.k8s, "k8s_conformance_image")

        steps_path = cfg.k8s_deploy.k8s_update_steps_path
        update_commands = self.__underlay.read_template(steps_path)
        self.execute_commands(
            update_commands, label="Updating kubernetes to '{}'".format(tag))

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
               raise_on_err=raise_on_err, verbose=True)

    def run_virtlet_conformance(self, timeout=60 * 120,
                                log_file='virtlet_conformance.log',
                                report_name="report.xml"):
        if self.__config.k8s.run_extended_virtlet_conformance:
            ci_image = "cloud-images.ubuntu.com/xenial/current/" \
                       "xenial-server-cloudimg-amd64-disk1.img"
            cmd = (r"set -o pipefail; "
                   r"docker run --net=host {0} /virtlet-e2e-tests "
                   r"-include-cloud-init-tests -junitOutput {3} "
                   r"-image {2} -sshuser ubuntu -memoryLimit 1024 "
                   r"-alsologtostderr -cluster-url http://127.0.0.1:8080 "
                   r"-ginkgo.focus '\[Conformance\]' "
                   r"| tee {1}".format(
                    self.__config.k8s_deploy.kubernetes_virtlet_image,
                    log_file, ci_image, report_name))
        else:
            cmd = (r"set -o pipefail; "
                   r"docker run --net=host {0} /virtlet-e2e-tests "
                   r"-junitOutput {2} "
                   r"-alsologtostderr -cluster-url http://127.0.0.1:8080 "
                   r"-ginkgo.focus '\[Conformance\]' "
                   r"| tee {1}".format(
                    self.__config.k8s_deploy.kubernetes_virtlet_image,
                    log_file, report_name))
        LOG.info("Executing: {}".format(cmd))
        with self.__underlay.remote(
                node_name=self.controller_name) as remote:
            result = remote.check_call(cmd, timeout=timeout)
            stderr = result['stderr']
            stdout = result['stdout']
            LOG.info("Test results stdout: {}".format(stdout))
            LOG.info("Test results stderr: {}".format(stderr))
        return result

    def start_k8s_cncf_verification(self, timeout=60 * 180):
        """
            Build sonobuoy using golang docker image and install it in system
            Then generate sonobuoy verification manifest using gen command
            and wait for it to end using status annotation
            TODO (vjigulin): All sonobuoy methods can be improved if we define
            correct KUBECONFIG env variable
        """
        cncf_cmd =\
            'docker run --network host --name sonobuoy golang:1.11 bash -c ' \
            '"go get -d -v github.com/heptio/sonobuoy && ' \
            'go install -v github.com/heptio/sonobuoy" && ' \
            'docker cp sonobuoy:/go/bin/sonobuoy /usr/local/bin/ && ' \
            'docker rm sonobuoy && ' \
            'sonobuoy gen | kubectl apply -f -'

        self.controller_check_call(cncf_cmd, timeout=900)

        sonobuoy_pod = self.api.pods.get('sonobuoy', 'heptio-sonobuoy')
        sonobuoy_pod.wait_running()

        def sonobuoy_status():
            annotations = sonobuoy_pod.read().metadata.annotations
            json_status = annotations['sonobuoy.hept.io/status']
            status = yaml.safe_load(json_status)['status']
            if status != 'running':
                LOG.info("CNCF status: {}".format(json_status))
            return yaml.safe_load(json_status)['status']

        LOG.info("Waiting for CNCF to complete")
        helpers.wait(
            lambda: sonobuoy_status() == 'complete',
            interval=120, timeout=timeout,
            timeout_msg="Timeout for CNCF reached."
        )

    def determine_conformance_node(self, target):
        masters_fqdn = self._salt.get_pillar(
            tgt='I@kubernetes:master', pillar='linux:network:fqdn')
        node_names = [v for pillar in masters_fqdn for
                      k, v in pillar.items()]
        return [node_name for node_name
                in node_names
                if node_name.startswith(target)][0]

    def start_conformance_inside_pod(self, cnf_type='k8s', timeout=60 * 60):
        """
        Create conformance pod and wait for results
        :param cnf_type: k8s or virtlet. choose what conformance you want
        :param timeout:
        :return:
        """
        if cnf_type == 'k8s':
            pod_mark = 'conformance'
        elif cnf_type == 'virtlet':
            pod_mark = 'virtlet-conformance'
        else:
            LOG.error("Unknown conformance type or it even not set")
            raise RuntimeError("Unknown conformance type")
        conformance_cmd = "kubectl apply -f /srv/kubernetes/{}.yml" \
                          "".format(pod_mark)
        self.controller_check_call(conformance_cmd, timeout=900)

        cnf_pod = self.api.pods.get(pod_mark, pod_mark)
        cnf_pod.wait_running()

        pod = cnf_pod.read()
        target = "{}.".format(pod.spec.node_name)

        self.conformance_node = self.determine_conformance_node(target)

        def cnf_status():
            pod = cnf_pod.read()
            status = pod.status.phase
            LOG.info("Conformance status: {}".format(status))
            return status

        LOG.info("Waiting for Conformance to complete")
        helpers.wait(
            lambda: cnf_status() in ('Succeeded', 'Failed'),
            interval=120, timeout=timeout,
            timeout_msg="Timeout for Conformance reached."
        )

        pod = cnf_pod.read()
        status = pod.status.phase
        if status == 'Failed':
            describe = "kubectl describe po {0} -n {0}".format(pod_mark)
            LOG.info(self.controller_check_call(describe, timeout=30))
            raise RuntimeError("Conformance failed")

    def get_node_name(self, tgt):
        res = [node_name for node_name in
               self.__underlay.node_names() if tgt in node_name]
        assert len(res) > 0, 'Can not find node name by tgt {}'.format(tgt)
        return res[0]

    def move_file_to_root_folder(self, filepath):
        cmd = "mv {0} /root/".format(filepath)
        if self.conformance_node:
            short_name = self.conformance_node.split('.')[0]
            LOG.info("Managing results on {}".format(self.conformance_node))
            step = {'cmd': cmd, 'node_name': self.get_node_name(
                tgt=short_name)}
            LOG.info('Move {0} to /root/ on {1}'.format(
                filepath, self.conformance_node))
            self.execute_command(step, 'Move files')
        else:
            LOG.info("Node is not properly set")

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
            if system == 'docker':
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
            else:
                # system is k8s
                pod_name = kwargs.get('pod_name')
                pod_namespace = kwargs.get('pod_namespace')
                cmd = 'kubectl cp \"{0}/{1}:/{2}\" \"{3}\"'.format(
                    pod_namespace, pod_name, file_path, out_dir)
                remote.check_call(cmd, raise_on_err=False)

    def download_k8s_logs(self, files):
        """
        Download JUnit report and conformance logs from cluster
        :param files:
        :return:
        """
        if self.conformance_node:
            node = self.conformance_node
        else:
            node = self.controller_name
        LOG.info("Trying to get logs at {}".format(node))
        master_host = self.__config.salt.salt_master_host
        with self.__underlay.remote(host=master_host) as r:
            for log_file in files:
                cmd = "scp -r \"{0}:/root/{1}\" /root/".format(
                    node, log_file)
                r.check_call(cmd, raise_on_err=True)
                LOG.info("Downloading the artifact {0}".format(log_file))
                r.download(destination=log_file, target=os.getcwd())
        self.store_server_version(os.path.join(os.getcwd(), 'env_k8s_version'))

    def combine_xunit(self, path, output):
        """
        Function to combine multiple xmls with test results to
        one.

        :param path: Path where xmls to combine located
        :param output: Path to xml file where output will stored
        :return:
        """
        if self.conformance_node:
            node = self.conformance_node
        else:
            node = self.controller_name
        LOG.info("Trying to combine xunit at {}".format(node))
        cmd = ("apt-get install python-setuptools -y; "
               "pip install "
               "https://github.com/mogaika/xunitmerge/archive/master.zip")
        LOG.debug('Installing xunitmerge')
        self._salt.cmd_run(tgt=node, cmd=cmd)
        LOG.debug('Merging xunit')
        cmd = ("cd {0}; arg=''; "
               "for i in $(ls | grep xml); "
               "do arg=\"$arg $i\"; done && "
               "xunitmerge $arg {1} || true".format(path, output))
        self._salt.cmd_run(tgt=node, cmd=cmd)

    def manage_cncf_archive(self):
        """
        Function to untar archive, move files that we are needs to the
        home folder, prepare it to downloading.
        Will generate files on controller node:
            e2e.log, junit_01.xml, cncf_results.tar.gz, version.txt
        :return:
        """

        cmd =\
            "rm -rf cncf_results.tar.gz result && " \
            "mkdir result && " \
            "mv *_sonobuoy_*.tar.gz cncf_results.tar.gz && " \
            "tar -C result -xzf cncf_results.tar.gz && " \
            "mv result/plugins/e2e/results/e2e.log . ; " \
            "mv result/plugins/e2e/results/junit_01.xml . ; " \
            "kubectl version > version.txt"

        self.controller_check_call(cmd, raise_on_err=False)

    @retry(100, exception=DevopsCalledProcessError, interval=20)
    def nslookup(self, host, src):
        """ Run nslookup on controller and return result """
        return self.controller_check_call("nslookup {0} {1}".format(host, src))

    @retry(100, exception=DevopsCalledProcessError, interval=20)
    def curl(self, url, *args):
        """
        Run curl on controller and return stdout

        :param url: url to curl
        :return: list of strings (with /n at end of every line)
        """
        args = list(args)
        args.append(url)
        cmd = "curl -s -S {}".format(
            " ".join(["'{}'".format(a.replace("'", "\\'")) for a in args]))
        result = self.controller_check_call(cmd)
        LOG.debug("{0}\nresult:\n{1}".format(cmd, result['stdout']))
        return result['stdout']

    def store_server_version(self, env_file_path):
        """Store Kubernetes server version in bash source file"""

        def digits(string):
            return ''.join(n for n in string if n.isdigit())

        ver = self.api.api_version.get_code()
        LOG.debug("Got Kubernetes server version:\n{0}".format(ver))

        env_version = ("export KUBE_SERVER_VERSION={0}.{1}\n"
                       "export KUBE_SERVER_GIT_VERSION={2}\n"
                       .format(digits(ver.major),
                               digits(ver.minor),
                               ver.git_version))

        LOG.info("Kubernetes server version is stored to {0}:\n{1}"
                 .format(env_file_path, env_version))
        with open(env_file_path, 'w') as kver:
            kver.write(env_version)


class K8SKubectlCli(object):
    """ Contain kubectl cli commands and api wrappers"""
    def __init__(self, manager):
        self._manager = manager

    def cli_run(self, namespace, name, image, port, replicas=1):
        cmd = "kubectl -n {0} run {1} --image={2} --port={3} --replicas={4}".\
            format(namespace, name, image, port, replicas)
        return self._manager.controller_check_call(cmd)

    def run(self, namespace, name, image, port, replicas=1):
        self.cli_run(namespace, name, image, port, replicas)
        return self._manager.api.deployments.get(
            namespace=namespace, name=name)

    def cli_expose(self, namespace, resource_type, resource_name,
                   service_name=None, port='', service_type='ClusterIP'):
        cmd = "kubectl -n {0} expose {1} {2} --port={3} --type={4}".format(
            namespace, resource_type, resource_name, port, service_type)
        if service_name is not None:
            cmd += " --name={}".format(service_name)
        return self._manager.controller_check_call(cmd)

    def expose(self, resource, service_name=None,
               port='', service_type='ClusterIP'):
        self.cli_expose(resource.namespace, resource.resource_type,
                        resource.name, service_name=service_name,
                        port=port, service_type=service_type)
        return self._manager.api.services.get(
            namespace=resource.namespace, name=service_name or resource.name)

    def cli_exec(self, namespace, pod_name, cmd, container=''):
        kubectl_cmd = "kubectl -n {0} exec --container={1} {2} -- {3}".format(
            namespace, container, pod_name, cmd)
        return self._manager.controller_check_call(kubectl_cmd)

    # def exec(...), except exec is statement in python
    def execute(self, pod, cmd, container=''):
        return self.cli_exec(pod.namespace, pod.name, cmd, container=container)

    def cli_annotate(self, namespace, resource_type, resource_name,
                     annotations, overwrite=False):
        cmd = "kubectl -n {0} annotate {1} {2} {3}".format(
            namespace, resource_type, resource_name, annotations)
        if overwrite:
            cmd += " --overwrite"
        return self._manager.controller_check_call(cmd)

    def annotate(self, resource, annotations, overwrite=False):
        return self.cli_annotate(resource.namespace, resource.resource_type,
                                 resource.name, annotations,
                                 overwrite=overwrite)


class K8SVirtlet(object):
    """ Contain virtlet-related methods"""
    def __init__(self, manager, namespace='kube-system'):
        self._manager = manager
        self._namespace = namespace

    def get_virtlet_node_pod(self, node_name):
        for pod in self._manager.api.pods.list(
                namespace=self._namespace, name_prefix='virtlet-'):
            if pod.read().spec.node_name == node_name:
                return pod
        return None

    def get_pod_dom_uuid(self, pod):
        uuid_name_map = self.virtlet_execute(
            pod.read().spec.node_name, 'virsh list --uuid --name')['stdout']
        for line in uuid_name_map:
            if line.rstrip().endswith("-{}".format(pod.name)):
                return line.split(" ")[0]
        raise Exception("Cannot detect uuid for pod {}".format(pod.name))

    def virsh_domstats(self, pod):
        """ get dict of vm stats """
        uuid = self.get_pod_dom_uuid(pod)
        result = self.virtlet_execute(
            pod.read().spec.node_name, 'virsh domstats {}'.format(uuid))
        stats = dict()
        for line in result['stdout']:
            if '=' in line:
                vals = line.strip().split('=')
                stats[vals[0]] = vals[1]
        return stats

    def virtlet_execute(self, node_name, cmd, container='libvirt'):
        """ execute command inside virtlet container """
        pod = self.get_virtlet_node_pod(node_name)
        return self._manager.kubectl.execute(pod, cmd, container)


class K8SSampleDeployment(object):
    """ Wrapper for deployment run=>expose=>check frequent combination """
    def __init__(self, manager, name,
                 namespace=None,
                 image='gcr.io/google-samples/node-hello:1.0',
                 port=8080,
                 replicas=2):
        namespace = namespace or manager.api.default_namespace

        self._manager = manager
        self._port = port
        self._deployment = \
            manager.kubectl.run(namespace, name,
                                image=image, port=port, replicas=replicas)
        self._index = 1  # used to generate svc name
        self._svc = None  # hold last created svc

    def wait_ready(self, timeout=300, interval=5):
        self._deployment.wait_ready(timeout=timeout, interval=interval)
        return self

    def svc(self):
        """ Return the last exposed service"""
        return self._svc

    def expose(self, service_type='ClusterIP'):
        service_name = "{0}-s{1}".format(self._deployment.name, self._index)
        self._index += 1
        self._svc = self._manager.kubectl.expose(
            self._deployment, port=self._port,
            service_name=service_name, service_type=service_type)
        return self._svc

    def curl(self, svc=None, external=False):
        if svc is None:
            svc = self.svc()
        url = "http://{0}:{1}".format(svc.get_ip(external), self._port)
        if external:
            return requests.get(url).text
        else:
            return self._manager.curl(url)

    def is_service_available(self, svc=None, external=False):
        return "Hello Kubernetes!" in self.curl(svc, external=external)

    def delete(self):
        for svc in self._manager.api.services.list_all(
                name_prefix="{}-s".format(self._deployment.name)):
            svc.delete()
        self._deployment.delete()
