import pytest
import sys
import os

from tcp_tests import logger
from tcp_tests import settings

sys.path.append(os.getcwd())
try:
    from tcp_tests.fixtures import config_fixtures
    from tcp_tests.managers import underlay_ssh_manager
    from tcp_tests.managers import saltmanager as salt_manager
except ImportError:
    print("ImportError: Run the application from the tcp-qa directory or "
          "set the PYTHONPATH environment variable to directory which contains"
          " ./tcp_tests")
    sys.exit(1)
LOG = logger.logger


def has_only_similar(values_by_nodes):
    """
    :param values_by_nodes:  dict
    :return: bool, True if all items in the dict have similar values
    """
    values = list(values_by_nodes.values())
    return all(value == values[0] for value in values)


def get_control_plane_targets():
    config = config_fixtures.config()
    underlay = underlay_ssh_manager.UnderlaySSHManager(config)
    saltmanager = salt_manager.SaltManager(config, underlay)
    targets = list()
    try:
        targets += saltmanager.run_state(
            "I@keystone:server", 'test.ping')[0]['return'][0].keys()
        targets += saltmanager.run_state(
            "I@nginx:server and not I@salt:master",
            "test.ping")[0]['return'][0].keys()
    except BaseException as err:
        LOG.warning("Can't retrieve data from Salt. \
            Maybe cluster is not deployed completely.\
            Err: {}".format(err))

    # TODO: add check for Manila  existence
    # # Commented to avoid fails during OpenStack updates.
    # # Anyway we don't have deployments with Manila yet
    # targets.append('share*')
    # TODO: add check for Tenant Telemetry  existence
    targets.append('mdb*')
    # TODO: add check for Barbican existence
    targets.append('kmn*')
    return targets


@pytest.fixture
def switch_to_proposed_pipelines(reclass_actions, salt_actions):
    reclass_actions.add_key(
        "parameters._param.jenkins_pipelines_branch",
        "release/proposed/2019.2.0",
        "cluster/*/infra/init.yml"
    )

    proposed_branch = "http://mirror.mirantis.com/update/proposed/"
    url_param = "parameters._param.linux_system_repo_update_url"
    reclass_actions.add_key(url_param, proposed_branch,
                            "cluster/*/infra/init.yml")
    reclass_actions.add_key(url_param, proposed_branch,
                            "cluster/*/openstack/init.yml")
    reclass_actions.add_key(url_param, proposed_branch,
                            "cluster/*/stacklight/init.yml")
    reclass_actions.add_key(url_param, proposed_branch,
                            "cluster/*/ceph/init.yml")

    salt_actions.run_state("*", "saltutil.refresh_pillar")
    salt_actions.enforce_state("I@jenkins:client", "jenkins.client")


class TestUpdateMcpCluster(object):
    """
    Following the steps in
    https://docs.mirantis.com/mcp/master/mcp-operations-guide/update-upgrade/minor-update.html#minor-update
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_drivetrain(self, salt_actions, drivetrain_actions,
                               show_step, _, switch_to_proposed_pipelines):
        """Updating DriveTrain component to release/proposed/2019.2.0 version

        Scenario:
            1. Add workaround for PROD-32751
            2. Run job git-mirror-downstream-mk-pipelines
            3. Run job git-mirror-downstream-pipeline-library
            4. If jobs are passed then start 'Deploy - upgrade MCP Drivetrain'

        Duration: ~70 min
        """
        salt = salt_actions
        dt = drivetrain_actions

        # #################### Add workaround for PROD-32751 #################
        show_step(1)

        # FIXME: workaround for PROD-32751
        salt.cmd_run("cfg01*", "cd /srv/salt/reclass; git add -u && \
                        git commit --allow-empty -m 'Cluster model update'")

        # ################### Downstream mk-pipelines #########################
        show_step(2)
        job_name = 'git-mirror-downstream-mk-pipelines'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        update_pipelines = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)

        assert update_pipelines == 'SUCCESS'

        # ################### Downstream pipeline-library ####################
        show_step(3)
        job_name = 'git-mirror-downstream-pipeline-library'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        update_pipeline_library = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters)

        assert update_pipeline_library == 'SUCCESS'

        # ################### Start 'Deploy - upgrade MCP Drivetrain' job #####
        show_step(4)

        job_name = 'upgrade-mcp-release'
        job_parameters = {
            'GIT_REFSPEC': 'release/proposed/2019.2.0',
            'MK_PIPELINES_REFSPEC': 'release/proposed/2019.2.0',
            'TARGET_MCP_VERSION': '2019.2.0'
        }
        update_drivetrain = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters,
            build_timeout=90*60)

        assert update_drivetrain == 'SUCCESS'

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_glusterfs(self, salt_actions, reclass_actions,
                              drivetrain_actions, show_step, _):
        """ Upgrade GlusterFS
        Scenario:
        1. In infra/init.yml in Reclass, add the glusterfs_version parameter
        2. Start linux.system.repo state
        3. Start "update-glusterfs" job
        4. Check version for GlusterFS servers
        5. Check version for GlusterFS clients

        """
        salt = salt_actions
        reclass = reclass_actions
        dt = drivetrain_actions

        # ############## Change reclass ######################################
        show_step(1)
        reclass.add_key(
            "parameters._param.linux_system_repo_mcp_glusterfs_version_number",
            "5",
            "cluster/*/infra/init.yml"
        )
        # ################# Run linux.system state ###########################
        show_step(2)
        salt.enforce_state("*", "linux.system.repo")

        # ############## Start deploy-upgrade-galera job #####################
        show_step(3)
        job_name = 'update-glusterfs'

        update_glusterfs = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            build_timeout=40 * 60)

        assert update_glusterfs == 'SUCCESS'

        # ################ Check GlusterFS version for servers ##############
        show_step(4)
        gluster_server_versions_by_nodes = salt.cmd_run(
            "I@glusterfs:server",
            "glusterd --version|head -n1")[0]

        assert has_only_similar(gluster_server_versions_by_nodes),\
            gluster_server_versions_by_nodes

        # ################ Check GlusterFS version for clients ##############
        show_step(5)
        gluster_client_versions_by_nodes = salt.cmd_run(
            "I@glusterfs:client",
            "glusterfs --version|head -n1")[0]

        assert has_only_similar(gluster_client_versions_by_nodes), \
            gluster_client_versions_by_nodes

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_galera(self, salt_actions, reclass_actions,
                           drivetrain_actions, show_step, _):
        """ Upgrade Galera automatically

        Scenario:
            1. Include the Galera upgrade pipeline job to DriveTrain
            2. Apply the jenkins.client state on the Jenkins nodes
            3. set the openstack_upgrade_enabled parameter to true
            4. Refresh pillars
            5. Add repositories with new Galera packages
            6. Start job from Jenkins
        """
        salt = salt_actions
        reclass = reclass_actions
        dt = drivetrain_actions
        # ################### Enable pipeline #################################
        show_step(1)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.upgrade_galera",
            "cluster/*/cicd/control/leader.yml")
        show_step(2)
        salt.enforce_state("I@jenkins:client", "jenkins.client")

        # ############### Enable automatic upgrade ############################
        show_step(3)
        reclass.add_bool_key("parameters._param.openstack_upgrade_enabled",
                             "True",
                             "cluster/*/infra/init.yml")

        show_step(4)
        salt.run_state("dbs*", "saltutil.refresh_pillar")

        # ############# Add repositories with new Galera packages #######
        show_step(5)
        salt.enforce_state("dbs*", "linux.system.repo")
        salt.enforce_state("cfg*", "salt.master")

        # #################### Login Jenkins on cid01 node ###################
        show_step(6)

        job_name = 'deploy-upgrade-galera'
        job_parameters = {
            'INTERACTIVE': 'false'
        }

        update_galera = dt.start_job_on_cid_jenkins(
            job_name=job_name,
            job_parameters=job_parameters,
            build_timeout=40 * 60)

        assert update_galera == 'SUCCESS'

    @pytest.fixture
    def disable_automatic_failover_neutron_for_test(self, salt_actions):
        """
        On each OpenStack controller node, modify the neutron.conf file
        Restart the neutron-server service
        """
        def comment_line(node, file_name, word):
            """
            Adds '#' before the specific line in specific file

            :param node: string, salt target of node where the file locates
            :param file_name: string, full path to the file
            :param word: string, the begin of line which should be commented
            :return: None
            """
            salt_actions.cmd_run(node,
                                 "sed -i 's/^{word}/#{word}/' {file}".
                                 format(word=word,
                                        file=file_name))

        def add_line(node, file_name, line):
            """
            Appends line to the end of file

            :param node: string, salt target of node where the file locates
            :param file_name: string, full path to the file
            :param line: string, line that should be added
            :return: None
            """
            salt_actions.cmd_run(node, "echo {line} >> {file}".format(
                    line=line,
                    file=file_name))

        neutron_conf = '/etc/neutron/neutron.conf'
        neutron_server = "I@neutron:server"
        # ########  Create backup for config file #######################
        salt_actions.cmd_run(
            neutron_server,
            "cp -p {file} {file}.backup".format(file=neutron_conf))

        # ## Change parameters in neutron.conf'
        comment_line(neutron_server, neutron_conf,
                     "allow_automatic_l3agent_failover",)
        comment_line(neutron_server, neutron_conf,
                     "allow_automatic_dhcp_failover")
        add_line(neutron_server, neutron_conf,
                 "allow_automatic_dhcp_failover = false")
        add_line(neutron_server, neutron_conf,
                 "allow_automatic_l3agent_failover = false")

        # ## Apply changed config to the neutron-server service
        result = salt_actions.cmd_run(neutron_server,
                                      "service neutron-server restart")
        # TODO: add check that neutron-server is up and running
        yield result
        # ## Revert file changes
        salt_actions.cmd_run(
            neutron_server,
            "cp -p {file}.backup {file}".format(file=neutron_conf))
        salt_actions.cmd_run(neutron_server,
                             "service neutron-server restart")

    @pytest.fixture
    def disable_neutron_agents_for_test(self, salt_actions):
        """
        Disable the neutron services before the test and
        enable it after test
        """
        result = salt_actions.cmd_run("I@neutron:server", """
                service neutron-dhcp-agent stop && \
                service neutron-l3-agent stop && \
                service neutron-metadata-agent stop && \
                service neutron-openvswitch-agent stop
                """)
        yield result
        #
        salt_actions.cmd_run("I@neutron:server", """
                service neutron-dhcp-agent start && \
                service neutron-l3-agent start && \
                service neutron-metadata-agent start && \
                service neutron-openvswitch-agent start
                """)
        # TODO: add check that all services are UP and running

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_rabbit(self, salt_actions, reclass_actions,
                           drivetrain_actions, show_step, _,
                           disable_automatic_failover_neutron_for_test,
                           disable_neutron_agents_for_test):
        """ Updates RabbitMQ
        Scenario:
            1. Include the RabbitMQ upgrade pipeline job to DriveTrain
            2. Add repositories with new RabbitMQ packages
            3. Start Deploy - upgrade RabbitMQ pipeline

        Updating RabbitMq should be completed before the OpenStack updating
        process starts
        """
        salt = salt_actions
        reclass = reclass_actions
        dt = drivetrain_actions

        # ####### Include the RabbitMQ upgrade pipeline job to DriveTrain ####
        show_step(1)
        reclass.add_class(
            "system.jenkins.client.job.deploy.update.upgrade_rabbitmq",
            "cluster/*/cicd/control/leader.yml")
        salt.enforce_state("I@jenkins:client", "jenkins.client")

        reclass.add_bool_key("parameters._param.openstack_upgrade_enabled",
                             "True",
                             "cluster/*/infra/init.yml")
        salt.run_state("I@rabbitmq:server", "saltutil.refresh_pillar")

        # ########### Add repositories with new RabbitMQ packages ############
        show_step(2)
        salt.enforce_state("I@rabbitmq:server", "linux.system.repo")

        # ########### Start Deploy - upgrade RabbitMQ pipeline  ############
        show_step(3)
        job_parameters = {
            'INTERACTIVE': 'false'
        }

        update_rabbit = dt.start_job_on_cid_jenkins(
            job_name='deploy-upgrade-rabbitmq',
            job_parameters=job_parameters,
            build_timeout=40 * 60
        )
        assert update_rabbit == 'SUCCESS'

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_ceph(self, salt_actions, drivetrain_actions, show_step, _):
        """ Updates Ceph to the latest minor version

        Scenario:
            1. Add workaround for unhealth Ceph
            2. Start ceph-upgrade job with default parameters
            3. Check Ceph version for all nodes

        https://docs.mirantis.com/mcp/master/mcp-operations-guide/update-upgrade/minor-update/ceph-update.html
        """
        salt = salt_actions
        dt = drivetrain_actions

        # ###################### Add workaround for unhealth Ceph ############
        show_step(1)
        salt.cmd_run("I@ceph:radosgw",
                     "ceph config set 'mon pg warn max object skew' 20")
        # ###################### Start ceph-upgrade pipeline #################
        show_step(2)
        job_parameters = {}

        update_ceph = dt.start_job_on_cid_jenkins(
            job_name='ceph-update',
            job_parameters=job_parameters)

        assert update_ceph == 'SUCCESS'

        # ########## Verify Ceph version #####################################
        show_step(3)

        ceph_version_by_nodes = salt.cmd_run(
          "I@ceph:* and not I@ceph:monitoring and not I@ceph:backup:server",
          "ceph version")[0]

        assert has_only_similar(ceph_version_by_nodes), ceph_version_by_nodes

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_stacklight(self, _, drivetrain_actions):
        """ Update packages for Stacklight
        Scenario:
        1. Start Deploy - upgrade Stacklight job
        """
        drivetrain = drivetrain_actions

        job_parameters = {
            "STAGE_UPGRADE_DOCKER_COMPONENTS": False,
            "STAGE_UPGRADE_ES_KIBANA": False,
            "STAGE_UPGRADE_SYSTEM_PART": False
        }
        upgrade_control_pipeline = drivetrain.start_job_on_cid_jenkins(
            job_name="stacklight-upgrade",
            job_parameters=job_parameters)

        assert upgrade_control_pipeline == 'SUCCESS'


class TestOpenstackUpdate(object):

    @pytest.mark.grab_versions
    @pytest.mark.run_mcp_update
    def test__pre_update__enable_pipeline_job(self,
                                              reclass_actions, salt_actions,
                                              show_step):
        """ Enable pipeline in the Drivetrain

        Scenario:
        1. Add deploy.update.* classes to the reclass
        2. Start jenkins.client salt state

        """
        salt = salt_actions
        reclass = reclass_actions
        show_step(1)
        reclass.add_class("system.jenkins.client.job.deploy.update.upgrade",
                          "cluster/*/cicd/control/leader.yml")

        reclass.add_class(
            "system.jenkins.client.job.deploy.update.upgrade_ovs_gateway",
            "cluster/*/cicd/control/leader.yml")

        reclass.add_class(
            "system.jenkins.client.job.deploy.update.upgrade_compute",
            "cluster/*/cicd/control/leader.yml")

        show_step(2)
        r, errors = salt.enforce_state("I@jenkins:client", "jenkins.client")
        assert errors is None

    @pytest.mark.grab_versions
    @pytest.mark.parametrize('target', get_control_plane_targets())
    @pytest.mark.run_mcp_update
    def test__update__control_plane(self, drivetrain_actions,
                                    switch_to_proposed_pipelines, target):
        """Start 'Deploy - upgrade control VMs' for specific node
        """
        job_parameters = {
            "TARGET_SERVERS": target,
            "INTERACTIVE": False}
        upgrade_control_pipeline = drivetrain_actions.start_job_on_cid_jenkins(
            job_name="deploy-upgrade-control",
            job_parameters=job_parameters)

        assert upgrade_control_pipeline == 'SUCCESS'

    @pytest.mark.grab_versions
    @pytest.mark.run_mcp_update
    def test__update__data_plane(self, drivetrain_actions):
        """Start 'Deploy - upgrade OVS gateway'
        """
        job_parameters = {
            "INTERACTIVE": False}
        upgrade_data_pipeline = drivetrain_actions.start_job_on_cid_jenkins(
            job_name="deploy-upgrade-ovs-gateway",
            job_parameters=job_parameters)

        assert upgrade_data_pipeline == 'SUCCESS'
