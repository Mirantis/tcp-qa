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

from tcp_tests import logger
from tcp_tests import settings

LOG = logger.logger


class TestMCPK8sActions(object):
    """Test class for different k8s actions"""

    @pytest.mark.grab_versions
    @pytest.mark.fail_snapshot
    @pytest.mark.cz8116
    def test_k8s_externaldns_coredns(self, show_step, config, k8s_deployed):
        """Test externaldns integration with coredns

        Scenario:
        1. Install k8s with externaldns addon enabled(including etcd, coredns)
        2. Start simple service
        3. Expose deployment
        4. Annotate service with domain name
        5. Try to get service using nslookup
        """

        if not (config.k8s_deploy.kubernetes_externaldns_enabled and
                config.k8s_deploy.kubernetes_coredns_enabled):
            pytest.skip("Test requires Externaldns and coredns addons enabled")

        show_step(1)
        k8sclient = k8s_deployed.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        show_step(2)
        name = 'test-nginx'
        k8s_deployed.kubectl_run(name, 'nginx', '80')

        show_step(3)
        k8s_deployed.kubectl_expose('deployment', name, '80', 'ClusterIP')

        hostname = "test.{0}.local.".format(settings.LAB_CONFIG_NAME)
        annotation = "\"external-dns.alpha.kubernetes.io/" \
                     "hostname={0}\"".format(hostname)
        show_step(4)
        k8s_deployed.kubectl_annotate('service', name, annotation)

        show_step(5)
        dns_host = k8s_deployed.get_svc_ip('coredns')
        k8s_deployed.nslookup(hostname, dns_host)

    @pytest.mark.grab_versions
    @pytest.mark.cncf_publisher(name=['e2e.log', 'junit_01.xml', 'version.txt',
                                      'cncf_results.tar.gz'])
    @pytest.mark.fail_snapshot
    def test_k8s_cncf_certification(self, show_step, config, k8s_deployed,
                                    cncf_log_helper):
        """Run cncf e2e suite and provide files needed for pull request
        to the CNCF repo

        Scenario:
        1. Run cncf from https://github.com/cncf/k8s-conformance
        """

        show_step(1)
        k8s_deployed.start_k8s_cncf_verification()

    @pytest.mark.grap_versions
    @pytest.mark.fail_snapshot
    def test_k8s_chain_update(self, show_step, config, k8s_deployed,
                              k8s_chain_update_log_helper):
        """Test for chain-upgrading k8s hypercube pool and checking it

        Scenario:
            1. Prepare salt on hosts
            2. Setup controller nodes
            3. Setup compute nodes
            4. Setup Kubernetes cluster
            5. Update hypercube, update pool
            6. Run conformance for updated cluster
            7. Go to step 5 if update chain is not ended
        """

        chain_versions = config.k8s.k8s_update_chain.split(" ")
        for version in chain_versions:
            show_step(5)
            k8s_deployed.update_k8s_images(version)

            show_step(6)
            LOG.info("Running conformance on {} version".format(version))
            k8s_deployed.run_conformance(log_out="k8s_conformance_{}.log".format(chain_versions.index(version)))

            show_step(7)
