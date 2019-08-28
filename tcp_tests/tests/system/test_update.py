import pytest

from tcp_tests import logger
from tcp_tests import settings
from tcp_tests.utils import run_jenkins_job
from tcp_tests.utils import get_jenkins_job_stages

LOG = logger.logger


class TestUpdateMcpCluster(object):
    """
    Following the steps in
    https://docs.mirantis.com/mcp/master/mcp-operations-guide/update-upgrade/minor-update.html#minor-update
    """

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_drivetrain(self, salt_actions, show_step, _):
        """Updating DriveTrain component to release/proposed/2019.2.0 version

        Scenario:
            1. Get CICD Jenkins access credentials from salt
            2. Run job git-mirror-downstream-mk-pipelines
            3. Run job git-mirror-downstream-pipeline-library
            4. If jobs are passed then start 'Deploy - upgrade MCP Drivetrain'

        Duration: ~35 min
        """
        salt = salt_actions
        jenkins_creds = salt.get_cluster_jenkins_creds()

        # #################### Login Jenkins on cid01 node ###################
        show_step(1)

        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
        jenkins_start_timeout = 60
        jenkins_build_timeout = 1800

        # FIXME: workaround for PROD-32751
        salt.cmd_run("cfg01*", "cd /srv/salt/reclass; git add -u && \
                        git commit --allow-empty -m 'Cluster model update'")

        # ################### Downstream mk-pipelines #########################
        show_step(2)
        job_name = 'git-mirror-downstream-mk-pipelines'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        update_pipelines = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=False,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_pipelines == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

        # ################### Downstream pipeline-library ####################
        show_step(3)
        job_name = 'git-mirror-downstream-pipeline-library'
        job_parameters = {
            'BRANCHES': 'release/proposed/2019.2.0'
        }
        update_pipeline_library = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=False,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_pipeline_library == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

        # ################### Start 'Deploy - upgrade MCP Drivetrain' job #####
        show_step(4)

        jenkins_build_timeout = 3600
        job_name = 'upgrade-mcp-release'
        job_parameters = {
            'MK_PIPELINES_REFSPEC': 'release/proposed/2019.2.0',
            'TARGET_MCP_VERSION': '2019.2.0'
        }
        update_drivetrain = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            start_timeout=jenkins_start_timeout,
            build_timeout=jenkins_build_timeout,
            verbose=False,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_drivetrain == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_glusterfs(self, salt_actions, reclass_actions,
                              show_step, _):
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
        jenkins_creds = salt.get_cluster_jenkins_creds()
        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
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
        jenkins_build_timeout = 40 * 60
        job_name = 'update-glusterfs'

        update_glusterfs = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            build_timeout=jenkins_build_timeout,
            verbose=False,
            job_name=job_name)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_glusterfs == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))

        # ################ Check GlusterFS version for servers ##############
        show_step(7)
        gluster_server_versions = salt.cmd_run("I@glusterfs:server",
                                               "glusterd --version|head -n1")

        def are_similar(x): return x == gluster_server_versions[0]
        assert all(map(are_similar, gluster_server_versions))

        # ################ Check GlusterFS version for clients ##############
        show_step(8)
        gluster_client_versions = salt.cmd_run("I@glusterfs:client",
                                               "glusterfs --version|head -n1")

        def are_similar(x): return x == gluster_client_versions[0]
        assert all(map(are_similar, gluster_client_versions))

    @pytest.mark.grab_versions
    @pytest.mark.parametrize("_", [settings.ENV_NAME])
    @pytest.mark.run_mcp_update
    def test_update_galera(self, salt_actions, reclass_actions, show_step, _):
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
        jenkins_creds = salt.get_cluster_jenkins_creds()
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
        salt.enforce_state("dbs*", "saltutil.refresh_pillar")

        # ############# Add repositories with new Galera packages #######
        show_step(5)
        salt.enforce_state("dbs*", "linux.system.repo")
        salt.enforce_state("cfg*", "salt.master")

        # #################### Login Jenkins on cid01 node ###################
        show_step(6)

        jenkins_url = jenkins_creds.get('url')
        jenkins_user = jenkins_creds.get('user')
        jenkins_pass = jenkins_creds.get('pass')
        jenkins_build_timeout = 40 * 60
        job_name = 'deploy-upgrade-galera'
        job_parameters = {
            'INTERACTIVE': 'false'
        }

        update_galera = run_jenkins_job.run_job(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            build_timeout=jenkins_build_timeout,
            verbose=False,
            job_name=job_name,
            job_parameters=job_parameters)

        (description, stages) = get_jenkins_job_stages.get_deployment_result(
            host=jenkins_url,
            username=jenkins_user,
            password=jenkins_pass,
            job_name=job_name,
            build_number='lastBuild')

        LOG.info(description)
        LOG.info('\n'.join(stages))

        assert update_galera == 'SUCCESS', "{0}\n{1}".format(
            description, '\n'.join(stages))
