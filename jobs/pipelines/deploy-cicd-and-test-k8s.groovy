@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()


node ("${NODE_NAME}") {
  try {

    stage("Clean the environment and clone tcp-qa") {
        shared.prepare_working_dir()
    }

    stage("Create environment, generate model, bootstrap the salt-cluster") {
        shared.swarm_bootstrap_salt_cluster_devops()
    }

    stage("Install core infrastructure and deploy CICD nodes") {
        shared.swarm_deploy_cicd(env.DRIVETRAIN_STACK_INSTALL)
    }

    stage("Install core infrastructure and deploy CICD nodes") {
        shared.swarm_deploy_platform(env.PLATFORM_STACK_INSTALL)
    }

    stage("Run tests") {
        shared.run_cmd("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_k8s

            # Prepare snapshots that may be used in tests if MANAGER=devops
            cp \$(pwd)/${ENV_NAME}_salt_deployed.ini \$(pwd)/${ENV_NAME}_k8s_deployed.ini
            cp \$(pwd)/${ENV_NAME}_salt_deployed.ini \$(pwd)/${ENV_NAME}_stacklight_deployed.ini
            #dos.py suspend ${ENV_NAME}
            #dos.py snapshot ${ENV_NAME} k8s_deployed
            #dos.py snapshot ${ENV_NAME} stacklight_deployed
            #dos.py resume ${ENV_NAME}
            #dos.py time-sync ${ENV_NAME}

            # Initialize variables used in tcp-qa tests
            export CURRENT_SNAPSHOT=stacklight_deployed  # provide the snapshot name required by the test
            export TESTS_CONFIGS=\$(pwd)/${ENV_NAME}_salt_deployed.ini  # some SSH data may be filled separatelly

            #export MANAGER=empty  # skip 'hardware' fixture, disable snapshot/revert features
            export MANAGER=devops  # use 'hardware' fixture to manage fuel-devops environment
            export MAKE_SNAPSHOT_STAGES=false  # skip 'hardware' fixture, disable snapshot/revert features
            # export SSH='{...}'  # non-empty SSH required to skip 'underlay' fixture. It is filled from TESTS_CONFIGS now
            export salt_master_host=\$SALT_MASTER_IP  # skip salt_deployed fixture
            export salt_master_port=6969
            export SALT_USER=\$SALTAPI_USER
            export SALT_PASSWORD=\$SALTAPI_PASS
            export CORE_INSTALLED=true  # skip core_deployed fixture
            export K8S_INSTALLED=true              # skip k8s_deployed fixture
            export sl_installed=true              # skip stacklight_deployed fixture

            py.test --junit-xml=nosetests.xml ${RUN_TEST_OPTS}

            dos.py suspend ${ENV_NAME}
            dos.py snapshot ${ENV_NAME} test_completed
            """)
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
    shared.run_cmd("""\
        dos.py suspend ${ENV_NAME} || true
        dos.py snapshot ${ENV_NAME} test_failed || true
        """)
      throw e
  } finally {
    // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
    // and report appropriate data to TestRail
    if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
        shared.run_cmd("""\
            dos.py destroy ${ENV_NAME} || true
        """)
    } else {
        shared.run_cmd("""\
            dos.py resume ${ENV_NAME} || true
            dos.py time-sync ${ENV_NAME} || true
        """)
    }
    shared.report_deploy_result("hardware,create_model,salt," + env.DRIVETRAIN_STACK_INSTALL + "," + env.PLATFORM_STACK_INSTALL)
    shared.report_test_result()
  }
}