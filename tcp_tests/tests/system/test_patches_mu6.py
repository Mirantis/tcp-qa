import pytest
from tcp_tests import logger

LOG = logger.logger


class TestAddressedIssuesMu6(object):
    """ Patches for MU6
    https://docs.mirantis.com/mcp/master/mcp-release-notes/mu/mu-6.html

    Issues resolutions requiring manual application
    """

    def test_gnocchi_measurements(self, show_step,
                                  salt_actions, reclass_actions):
        """Apply fix for '[32645] Missing measurements in Gnocchi on
        environments with Barbican'

        Scenario:
        1. Update reclass with ks_notifications items
        2. Run keystone.server state for @keystone targets
        3. Run barbican.server state for @barbican targets

        https://docs.mirantis.com/mcp/master/mcp-release-notes/mu/mu-6/mu-6-addressed/mu-6-os/mu6-os-manual.html#missing-measurements-in-gnocchi-on-environments-with-barbican

        """
        reclass = reclass_actions
        salt = salt_actions
        # ### Skip test if cluster without barbican ###########################
        if not salt.get_single_pillar('I@salt:master',
                                      '_param:barbican_enabled'):
            pytest.skip("Test is skipped due to absent barbican component")

        # ############# Update reclass with ks_notifications items ############
        show_step(1)
        reclass.add_key("parameters._param.keystone_notification_topics",
                        "${_param:openstack_notification_topics},barbican",
                        "classes/cluster/*/openstack/init.yml")

        reclass.add_key("parameters.barbican.server.ks_notifications_topic",
                        "barbican",
                        "classes/cluster/*/openstack/barbican.yml")

        salt.run_state("I@keystone:server", "saltutil.refresh_pillar")
        salt.run_state("I@barbican:server", "saltutil.refresh_pillar")

        # ############ Run keystone.server state for @keystone ################
        show_step(2)
        salt.enforce_state("I@keystone:server:role:primary",
                           "keystone.server")
        salt.enforce_state("I@keystone:server",
                           "keystone.server")

        # ############ Run barbican.server state for @barbican ################
        salt.enforce_state("I@barbican:server:role:primary",
                           "barbican.server")
        salt.enforce_state("I@barbican:server",
                           "barbican.server")

    def test_stacklight_sf_notifier_sfdc_sandbox_enabled(
            self, show_step,
            salt_actions, reclass_actions):
        """ Apply fix for 'StackLight deployment fails with stack creation
        failed error'

        Scenario:
        1. Add sf_notifier_sfdc_sandbox_enabled to reclass
        2. Apply docker.client state for Prometheus

        https://docs.mirantis.com/mcp/master/mcp-release-notes/mu/mu-6/mu-6-addressed/mu-6-sl/mu6-sl-manual.html#stacklight-deployment-fails-with-stack-creation-failed-error

        """
        reclass = reclass_actions
        salt = salt_actions

        # ##### Add sf_notifier_sfdc_sandbox_enabled to reclass ##############
        show_step(1)
        # Yes, here "True" should be as a string, it's not a mistake!
        reclass.add_key("parameters._param.sf_notifier_sfdc_sandbox_enabled",
                        "True",
                        "classes/cluster/*/stacklight/server.yml")

        # ############### Apply states for Prometheus ########################
        show_step(2)
        tgt = "I@prometheus:server and I@docker:client"

        salt.run_state(tgt, "saltutil.refresh_pillar")
        salt.enforce_state(tgt, "docker.client")

    def test_aptly_haproxy_for_online_deployments(
            self, show_step,
            salt_actions, reclass_actions):
        """ Apply fix for '[32133] HAProxy status is down for aptly-public
        in online deployments'

        Scenario:
        1. Remove system.haproxy.proxy.listen.cicd.aptly from reclass
        2. Apply haproxy.proxy state for Haproxy on the cid* nodes

        """
        reclass = reclass_actions
        salt = salt_actions

        # ##### Remove system.haproxy.proxy.listen.cicd.aptly from reclass ###
        show_step(1)
        reclass.del_class("system.haproxy.proxy.listen.cicd.aptly",
                          "cluster/*/cicd/control/init.yml")

        # ############### Apply states for Haproxy  ##########################
        show_step(2)
        tgt = "I@jenkins:client and I@haproxy:proxy"

        salt.run_state(tgt, "saltutil.refresh_pillar")
        salt.enforce_state(tgt, "haproxy.proxy")
