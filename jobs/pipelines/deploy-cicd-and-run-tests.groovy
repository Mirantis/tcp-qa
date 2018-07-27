@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()
def steps = "hardware,create_model,salt," + env.DRIVETRAIN_STACK_INSTALL + "," + env.PLATFORM_STACK_INSTALL

node ("${NODE_NAME}") {
  try {

    stage("Clean the environment and clone tcp-qa") {
        shared.prepare_working_dir()
    }

    stage("Create environment, generate model, bootstrap the salt-cluster") {
        // steps: "hardware,create_model,salt"
        shared.swarm_bootstrap_salt_cluster_devops()
    }

    stage("Install core infrastructure and deploy CICD nodes") {
        // steps: env.DRIVETRAIN_STACK_INSTALL
        shared.swarm_deploy_cicd(env.DRIVETRAIN_STACK_INSTALL)
    }

    stage("Install core infrastructure and deploy CICD nodes") {
        // steps: env.PLATFORM_STACK_INSTALL
        shared.swarm_deploy_platform(env.PLATFORM_STACK_INSTALL)
    }

    stage("Run tests") {
        shared.swarm_run_pytest(steps)
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
    if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "false") {
        shared.run_cmd("""\
            dos.py resume ${ENV_NAME} || true
            sleep 20    # Wait for I/O on the host calms down
            dos.py time-sync ${ENV_NAME} || true
        """)
    } else {
        shared.run_cmd("""\
            dos.py destroy ${ENV_NAME} || true
        """)
    }
    shared.report_deploy_result(steps)
    shared.report_test_result()
  }
}
