@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()
def steps = "hardware,create_model,salt," + env.DRIVETRAIN_STACK_INSTALL + "," + env.PLATFORM_STACK_INSTALL

currentBuild.description = "${NODE_NAME}:${ENV_NAME}"

def deploy(shared, common) {
    def report_text = ''
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

        currentBuild.result = 'SUCCESS'

    } catch (e) {
        common.printMsg("Deploy is failed: " + e.message , "red")
        shared.run_cmd("""\
            dos.py suspend ${ENV_NAME} || true
            dos.py snapshot ${ENV_NAME} deploy_failed || true
        """)
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
        report_text = e.message
        throw e
    } finally {
        shared.create_deploy_result_report(steps, currentBuild.result, report_text)
    }
}

def test(shared, common) {
    try {
        stage("Run tests") {
            shared.swarm_run_pytest(steps)
        }

    } catch (e) {
        common.printMsg("Tests are failed: " + e.message, "red")
        shared.run_cmd("""\
            dos.py suspend ${ENV_NAME} || true
            dos.py snapshot ${ENV_NAME} tests_failed || true
        """)
        throw e
    } finally {
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
    }
}

// main
throttle(['fuel_devops_environment']) {
  node ("${NODE_NAME}") {
    try {
        deploy()
        //deploy(shared, common)
        test(shared, common)
    } catch (e) {
        common.printMsg("Job is failed: " + e.message, "red")
        currentBuild.result = 'FAILURE'
    } finally {
        shared.swarm_testrail_report(steps)
    }
  }
}