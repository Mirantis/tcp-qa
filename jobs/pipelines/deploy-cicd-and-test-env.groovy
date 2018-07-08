@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()


node ("${NODE_NAME}") {
  try {

    stage("Clean the environment and clone tcp-qa") {
        shared.prepare_working_dir()
    }

    stage("Create environment, generate mode, bootstrap the salt-cluster") {
        shared.swarm_bootstrap_salt_cluster_devops()
    }

    stage("Install core infrastructure and deploy CICD nodes") {
        shared.swarm_deploy_cicd(stack_to_install='core,cicd')
    }

    stage("Install core infrastructure and deploy CICD nodes") {
        shared.swarm_deploy_stacks(stack_to_install="${STACK_INSTALL}")
    }

    stage("Run tests") {
        shared.run_cmd("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_k8s

            # Initialize variables used in tcp-qa tests
            export CURRENT_SNAPSHOT=sl_deployed  # provide the snapshot name required by the test
            export TESTS_CONFIGS=\$(pwd)/${ENV_NAME}_salt_deployed.ini  # some SSH data may be filled separatelly

            export MANAGER=empty  # skip 'hardware' fixture, disable snapshot/revert features
            # export SSH='{...}'  # non-empty SSH required to skip 'underlay' fixture. It is filled from TESTS_CONFIGS now
            export salt_master_host=\$SALT_MASTER_IP  # skip salt_deployed fixture
            export salt_master_port=6969
            export SALT_USER=\$SALTAPI_USER
            export SALT_PASSWORD=\$SALTAPI_PASS
            export COMMON_SERVICES_INSTALLED=true  # skip common_services_deployed fixture
            export OPENSTACK_INSTALLED=true              # skip k8s_deployed fixture
            export sl_installed=true              # skip sl_deployed fixture

            py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -k test_mcp_pike_cookied_ovs_install

            #dos.py suspend ${ENV_NAME}
            #dos.py snapshot ${ENV_NAME} test_completed
            #dos.py resume ${ENV_NAME}
            #dos.py time-sync ${ENV_NAME}
            """)
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
      throw e
  } finally {
    // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
    // and report appropriate data to TestRail
    if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
        shared.run_cmd("""\
            dos.py destroy ${ENV_NAME}
        """)
    }
  }
}