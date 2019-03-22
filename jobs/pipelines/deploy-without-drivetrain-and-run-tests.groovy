@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()
def steps = "hardware,create_model,salt," + env.DRIVETRAIN_STACK_INSTALL + "," + env.PLATFORM_STACK_INSTALL

currentBuild.description = "${NODE_NAME}:${ENV_NAME}"

def deploy(shared, common, steps) {
    def report_text = ''
    try {

        stage("Clean the environment and clone tcp-qa") {
            shared.prepare_working_dir()
        }

        stage("Create environment, generate model, bootstrap the salt-cluster") {
            // steps: "hardware,create_model,salt"
            shared.swarm_bootstrap_salt_cluster_devops()
        }

        stage("Deploy platform components from day01 Jenkins") {
            // steps: env.PLATFORM_STACK_INSTALL
            shared.swarm_deploy_platform_non_cicd(env.PLATFORM_STACK_INSTALL, env.PLATFORM_STACK_INSTALL_TIMEOUT)
        }

        currentBuild.result = 'SUCCESS'

    } catch (e) {
        common.printMsg("Deploy is failed: " + e.message , "purple")
        report_text = e.message
        def snapshot_name = "deploy_failed"
        shared.run_cmd("""\
            dos.py suspend ${ENV_NAME} || true
            dos.py snapshot ${ENV_NAME} ${snapshot_name} || true
        """)
        if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "false") {
            shared.run_cmd("""\
                dos.py resume ${ENV_NAME} || true
            """)
        }
        shared.devops_snapshot_info(snapshot_name)
        throw e
    } finally {
        shared.create_deploy_result_report(steps, currentBuild.result, report_text)
    }
}

def test(shared, common, steps) {
    try {
        stage("Run tests") {
            shared.swarm_run_pytest(steps, "${NODE_NAME}")
        }

    } catch (e) {
        common.printMsg("Tests are failed: " + e.message, "purple")
        def snapshot_name = "tests_failed"
        shared.run_cmd("""\
            dos.py suspend ${ENV_NAME} || true
            dos.py snapshot ${ENV_NAME} ${snapshot_name} || true
        """)
        if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "false") {
            shared.run_cmd("""\
                dos.py resume ${ENV_NAME} || true
            """)
        }
        shared.devops_snapshot_info(snapshot_name)
        throw e
    }
}

// main
// Temporary disable throttle to check how it will run
//throttle(['fuel_devops_environment']) {
  node ("${NODE_NAME}") {
    try {
        // run deploy stages
        deploy(shared, common, steps)
        // run test stages
        test(shared, common, steps)
    } catch (e) {
        common.printMsg("Job is failed: " + e.message, "purple")
        throw e
    } finally {
        // shutdown the environment if required
        if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
            shared.run_cmd("""\
                dos.py destroy ${ENV_NAME} || true
            """)
        }

        stage("Archive all xml reports") {
            archiveArtifacts artifacts: "**/*.xml,**/*.ini,**/*.log,**/*.tar.gz"
        }
        stage("report results to testrail") {
            shared.swarm_testrail_report(steps, "${NODE_NAME}")
        }
        stage("Store TestRail reports to job description") {
            def String description = readFile("description.txt")
            currentBuild.description += "\n${description}"
        }

    }
  }
//}