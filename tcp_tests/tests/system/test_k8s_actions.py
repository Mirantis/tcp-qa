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

import pytest
import netaddr
import os
import yaml

from tcp_tests import logger
from tcp_tests import settings

from tcp_tests.managers.k8s import read_yaml_file

LOG = logger.logger


class TestMCPK8sActions(object):
    """Test class for different k8s actions"""

    def __read_testdata_yaml(self, name):
        dir = os.path.join(os.path.dirname(__file__), 'testdata/k8s')
        return read_yaml_file(dir, name)

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cz8116
    @pytest.mark.k8s_calico
    def test_k8s_externaldns_coredns(self, show_step, config, k8s_deployed):
        """Test externaldns integration with coredns

        Scenario:
        1. Install k8s with externaldns addon enabled(including etcd, coredns)
        2. Start simple service
        3. Expose deployment
        4. Annotate service with domain name
        5. Try to get service using nslookup
        6. Delete service and deployment
        """

        show_step(1)
        if not (config.k8s_deploy.kubernetes_externaldns_enabled and
                config.k8s_deploy.kubernetes_coredns_enabled):
            pytest.skip("Test requires externaldns and coredns addons enabled")

        show_step(2)
        deployment = k8s_deployed.run_sample_deployment('test-dep')

        show_step(3)
        svc = deployment.expose()

        show_step(4)
        hostname = "test.{0}.local.".format(settings.LAB_CONFIG_NAME)
        svc.patch({
            "metadata": {
                "annotations": {
                    "external-dns.alpha.kubernetes.io/hostname": hostname
                }
            }
        })

        show_step(5)
        k8s_deployed.nslookup(hostname, svc.get_ip())

        show_step(6)
        deployment.delete()

    @pytest.mark.grab_versions
    @pytest.mark.cncf_publisher(name=['e2e.log', 'junit_01.xml', 'version.txt',
                                      'cncf_results.tar.gz'])
    @pytest.mark.fail_snapshot
    def test_k8s_cncf_certification(self, show_step, config, k8s_deployed,
                                    k8s_cncf_log_helper):
        """Run cncf e2e suite and provide files needed for pull request
        to the CNCF repo

        Scenario:
        1. Run cncf from https://github.com/cncf/k8s-conformance
        """

        show_step(1)
        k8s_deployed.start_k8s_cncf_verification()

    @pytest.mark.grap_versions
    @pytest.mark.fail_snapshot
    def test_k8s_chain_update(self, show_step, underlay, config, k8s_deployed,
                              k8s_chain_update_log_helper):
        """Test for chain-upgrading k8s hypercube pool and checking it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Run and expose sample test service
            6. Run conformance to check consistency
            7. For every version in update chain:
               Update cluster to new version, check test sample service
               availability, run conformance
            8. Delete service and deployment
        """

        show_step(5)
        sample = k8s_deployed.run_sample_deployment('test-dep-chain-upgrade')
        sample.expose()
        sample.wait_ready()

        assert sample.is_service_available()

        show_step(6)
        k8s_deployed.run_conformance(log_out="k8s_conformance.log")

        show_step(7)
        chain_versions = config.k8s.k8s_update_chain.split(" ")
        for version in chain_versions:
            LOG.info("Chain update to '{}' version".format(version))
            k8s_deployed.update_k8s_version(version)

            LOG.info("Checking test service availability")
            assert sample.is_service_available()

            LOG.info("Running conformance on {} version".format(version))
            log_name = "k8s_conformance_{}.log".format(version)
            k8s_deployed.run_conformance(log_out=log_name, raise_on_err=False)

        assert sample.is_service_available()

        show_step(8)
        sample.delete()

    @pytest.mark.grap_versions
    @pytest.mark.fail_snapshot
    def test_k8s_metallb(self, show_step, config, k8s_deployed):
        """Enable metallb in cluster and do basic tests

        Scenario:
            1. Setup Kubernetes cluster with enabled metallb
            2. Check that metallb pods created in metallb-system namespace
            3. Run 5 sample deployments
            4. Expose deployments with type=LoadBalancer
            5. Check services availability from outside of cluster
            6. Run conformance
            7. Check services availability from outside of cluster
            8. Delete deployments
        """
        show_step(1)
        if not config.k8s_deploy.kubernetes_metallb_enabled:
            pytest.skip("Test requires metallb addon enabled")

        show_step(2)
        ns = "metallb-system"
        assert \
            len(k8s_deployed.api.pods.list(ns, name_prefix="controller")) > 0
        assert \
            len(k8s_deployed.api.pods.list(ns, name_prefix="speaker")) > 0

        show_step(3)
        samples = []
        for i in range(5):
            name = 'test-dep-metallb-{}'.format(i)
            samples.append(k8s_deployed.run_sample_deployment(name))

        show_step(4)
        for sample in samples:
            sample.expose('LoadBalancer')
            sample.wait_ready()

        show_step(5)
        for sample in samples:
            assert sample.is_service_available(external=False)
            assert sample.is_service_available(external=True)

        show_step(6)
        k8s_deployed.run_conformance()

        show_step(7)
        for sample in samples:
            assert sample.is_service_available(external=False)
            assert sample.is_service_available(external=True)

        show_step(8)
        for sample in samples:
            sample.delete()

    @pytest.mark.grap_versions
    @pytest.mark.fail_snapshot
    def test_k8s_genie_flannel(self, show_step, config,
                               salt_deployed, k8s_deployed):
        """Test genie-cni+flannel cni setup

        Scenario:
            1. Setup Kubernetes cluster with genie cni and flannel
            2. Check that flannel pods created in kube-system namespace
            3. Create sample deployment with flannel cni annotation
            4. Check that the deployment have 1 ip addresses from cni provider
            5. Create sample deployment with calico cni annotation
            6. Check that the deployment have 1 ip addresses from cni provider
            7. Create sample deployment with multi-cni annotation
            8. Check that the deployment have 2 ip addresses from different
            cni providers
            9. Create sample deployment without cni annotation
            10. Check that the deployment have 1 ip address
            11. Check pods availability
            12. Run conformance
            13. Check pods availability
            14. Delete pods
        """
        show_step(1)

        # Find out calico and flannel networks
        tgt_k8s_control = "I@kubernetes:control:enabled:True"

        flannel_pillar = salt_deployed.get_pillar(
            tgt=tgt_k8s_control,
            pillar="kubernetes:master:network:flannel:private_ip_range")[0]
        flannel_network = netaddr.IPNetwork(flannel_pillar.values()[0])
        LOG.info("Flannel network: {}".format(flannel_network))

        calico_network_pillar = salt_deployed.get_pillar(
            tgt=tgt_k8s_control, pillar="_param:calico_private_network")[0]
        calico_netmask_pillar = salt_deployed.get_pillar(
            tgt=tgt_k8s_control, pillar="_param:calico_private_netmask")[0]
        calico_network = netaddr.IPNetwork(
            "{0}/{1}".format(calico_network_pillar.values()[0],
                             calico_netmask_pillar.values()[0]))
        LOG.info("Calico network: {}".format(calico_network))

        show_step(2)
        assert k8s_deployed.api.pods.list(
            namespace="kube-system", name_prefix="kube-flannel-") > 0

        show_step(3)
        flannel_pod = k8s_deployed.api.pods.create(
            body=self.__read_testdata_yaml('pod-sample-flannel.yaml'))
        flannel_pod.wait_running()

        show_step(4)
        flannel_ips = k8s_deployed.get_pod_ips_from_container(flannel_pod.name)
        assert len(flannel_ips) == 1
        assert netaddr.IPAddress(flannel_ips[0]) in flannel_network

        show_step(5)
        calico_pod = k8s_deployed.api.pods.create(
            body=self.__read_testdata_yaml('pod-sample-calico.yaml'))
        calico_pod.wait_running()

        show_step(6)
        calico_ips = k8s_deployed.get_pod_ips_from_container(calico_pod.name)
        assert len(calico_ips) == 1
        assert netaddr.IPAddress(calico_ips[0]) in calico_network

        show_step(7)
        multicni_pod = k8s_deployed.api.pods.create(
            body=self.__read_testdata_yaml('pod-sample-multicni.yaml'))
        multicni_pod.wait_running()

        show_step(8)
        multicni_ips = \
            k8s_deployed.get_pod_ips_from_container(multicni_pod.name)
        assert len(multicni_ips) == 2
        for net in [calico_network, flannel_network]:
            assert netaddr.IPAddress(multicni_ips[0]) in net or \
                   netaddr.IPAddress(multicni_ips[1]) in net

        show_step(9)
        nocni_pod = k8s_deployed.api.pods.create(
            body=self.__read_testdata_yaml('pod-sample.yaml'))
        nocni_pod.wait_running()

        show_step(10)
        nocni_ips = k8s_deployed.get_pod_ips_from_container(nocni_pod.name)
        assert len(nocni_ips) == 1
        assert (netaddr.IPAddress(nocni_ips[0]) in calico_network or
                netaddr.IPAddress(nocni_ips[0]) in flannel_network)

        show_step(11)

        def check_pod_availability(ip):
            assert "Hello Kubernetes!" in k8s_deployed.curl(
                "http://{}:8080".format(ip))

        def check_pods_availability():
            check_pod_availability(flannel_ips[0])
            check_pod_availability(calico_ips[0])
            check_pod_availability(multicni_ips[0])
            check_pod_availability(multicni_ips[1])
            check_pod_availability(nocni_ips[0])

        check_pods_availability()

        show_step(12)
        k8s_deployed.run_conformance()

        show_step(13)
        check_pods_availability()

        show_step(14)
        flannel_pod.delete()
        calico_pod.delete()
        multicni_pod.delete()
        nocni_pod.delete()

    @pytest.mark.grap_versions
    # @pytest.mark.fail_snapshot
    def test_k8s_dashboard(self, show_step, config,
                           salt_deployed, k8s_deployed):
        """Test dashboard setup

        Scenario:
            1. Setup Kubernetes cluster
            2. Try to curl login status page of dashboard
            3. Create a test-admin-user account
            4. Try to login in dashboard using test-admin-user account
            5. Get and check list of namespaces using dashboard api
        """
        show_step(1)

        show_step(2)
        ns = 'kube-system'
        dashboard_service =\
            k8s_deployed.api.services.get('kubernetes-dashboard', ns)
        dashboard_url = 'https://{}'.format(dashboard_service.get_ip())

        def dashboard_curl(url, data=None, headers=None):
            """ Why using curl from controller node:
                - connect_{get,post}_namespaced_service_proxy_with_path -
                  k8s lib does not provide way to pass headers or POST data
                - rest k8s api - need to auth
                - new load-balancer svc for dashboard + requests python lib -
                  requires working metallb or other load-balancer
            """
            args = ['--insecure']
            for name in headers or {}:
                args.append('--header')
                args.append("{0}: {1}".format(name, headers[name]))
            if data is not None:
                args.append('--data')
                args.append(data)
            result = k8s_deployed.curl(dashboard_url + url, *args)
            from pprint import pprint
            pprint(result)
            return ''.join(result)

        assert 'tokenPresent' in dashboard_curl('/api/v1/login/status')

        show_step(3)
        account = k8s_deployed.api.serviceaccounts.create(
            namespace=ns,
            body=self.__read_testdata_yaml('test-admin-user-account.yaml'))

        k8s_deployed.api.clusterrolebindings.create(
            body=self.__read_testdata_yaml(
                'test-admin-user-cluster-role-bind.yaml'))

        account.wait_secret_generation()
        account_secret = account.read().secrets[0]
        account_token = k8s_deployed.api.secrets.get(
            namespace=ns, name=account_secret.name).read().data['token']

        show_step(4)
        csrf_token = yaml.safe_load(dashboard_curl(
            '/api/v1/csrftoken/login'))['token']
        headers = {'X-CSRF-TOKEN': csrf_token,
                   'Content-Type': 'application/json'}
        headers['jweToken'] = yaml.safe_load(dashboard_curl(
            '/api/v1/login', headers=headers,
            data=yaml.safe_dump({'token': account_token})))['jweToken']

        show_step(5)
        from pprint import pprint
        pprint(dashboard_curl('/api/v1/namespace', headers=headers))
