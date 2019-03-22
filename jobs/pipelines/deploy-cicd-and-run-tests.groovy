@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()
def steps = "hardware,create_model,salt," + env.DRIVETRAIN_STACK_INSTALL + "," + env.PLATFORM_STACK_INSTALL
def env_manager = env.ENV_MANAGER ?: 'devops'

def jenkins_slave_node_name = "${NODE_NAME}"

//if (env_manager == 'devops') {
//    // Use the current node to create fuel-devops environment
//    jenkins_slave_node_name = "${NODE_NAME}"
//} else if (env_manager == 'heat') {
//    // Use spawned in the OpenStack stack the Jenkins slave node
//    //  with the following agent name
//    jenkins_slave_node_name = "openstack_slave_${JOB_NAME}_${BUILD_ID}"
//} else {
//    throw new Exception("Unknow env_manager: '${env_manager}'")
//}

currentBuild.description = "${NODE_NAME}:${ENV_NAME}"

def deploy(shared, common, steps, jenkins_slave_node_name) {
    def report_text = ''
    try {

        stage("Clean the environment and clone tcp-qa") {
            shared.prepare_working_dir(env_manager)
        }

        stage("Create environment, generate model, bootstrap the salt-cluster") {
            // steps: "hardware,create_model,salt"
            if (env_manager == 'devops') {
                jenkins_slave_node_name = "${NODE_NAME}"
                shared.swarm_bootstrap_salt_cluster_devops()
            } else if (env_manager == 'heat') {
                def new_jenkins_slave_node_name = "openstack_slave_${JOB_NAME}_${BUILD_ID}"
                // If shared.swarm_bootstrap_salt_cluster_heat() failed,
                // do not schedule shared.swarm_testrail_report() on the non existing Jenkins slave
                shared.swarm_bootstrap_salt_cluster_heat(new_jenkins_slave_node_name)
                // When the Heat stack created, set jenkins_slave_node_name to the new Jenkins slave
                jenkins_slave_node_name = new_jenkins_slave_node_name
            } else {
                throw new Exception("Unknow env_manager: '${env_manager}'")
            }
        }

        stage("Install core infrastructure and deploy CICD nodes") {
        if (env.DRIVETRAIN_STACK_INSTALL) {
                // steps: env.DRIVETRAIN_STACK_INSTALL
                shared.swarm_deploy_cicd(env.DRIVETRAIN_STACK_INSTALL, env.DRIVETRAIN_STACK_INSTALL_TIMEOUT, jenkins_slave_node_name)
            } else {
                common.printMsg("DRIVETRAIN_STACK_INSTALL is empty, skipping 'swarm-deploy-cicd' job", "green")
            }
        }

        stage("Deploy platform components") {
            if (env.PLATFORM_STACK_INSTALL) {
                // steps: env.PLATFORM_STACK_INSTALL
                shared.swarm_deploy_platform(env.PLATFORM_STACK_INSTALL, env.PLATFORM_STACK_INSTALL_TIMEOUT, jenkins_slave_node_name)
            } else {
                common.printMsg("PLATFORM_STACK_INSTALL is empty, skipping 'swarm-deploy-platform' job", "green")
            }
        }

        currentBuild.result = 'SUCCESS'

    } catch (e) {
        common.printMsg("Deploy is failed: " + e.message , "purple")
        report_text = e.message
        if (env_manager == 'devops') {
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
        }
        throw e
    } finally {
        shared.create_deploy_result_report(steps, currentBuild.result, report_text)
    }
}

def test(shared, common, steps, jenkins_slave_node_name) {
    try {
        stage("Run tests") {
            if (env.RUN_TEST_OPTS) {
                shared.swarm_run_pytest(steps, jenkins_slave_node_name)
            } else {
                common.printMsg("RUN_TEST_OPTS is empty, skipping 'swarm-run-pytest' job", "green")
            }
        }

    } catch (e) {
        common.printMsg("Tests are failed: " + e.message, "purple")
        if (env_manager == 'devops') {
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
        }
        throw e
    }
}

// main
// Temporary disable throttle to check how it will run
//throttle(['fuel_devops_environment']) {
  node ("${NODE_NAME}") {
    try {
        // run deploy stages
        deploy(shared, common, steps, jenkins_slave_node_name)
        // run test stages
        test(shared, common, steps, jenkins_slave_node_name)
    } catch (e) {
        common.printMsg("Job is failed: " + e.message, "purple")
        throw e
    } finally {
        if (env_manager == 'devops') {
            // shutdown the environment if required
            if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
                shared.run_cmd("""\
                    dos.py destroy ${ENV_NAME} || true
                """)
            }
        }

        stage("Archive all xml reports") {
            archiveArtifacts artifacts: "**/*.xml,**/*.ini,**/*.log,**/*.tar.gz"
        }

        if (env.REPORT_TO_TESTRAIL ?: true) {
            stage("report results to testrail") {
                shared.swarm_testrail_report(steps, jenkins_slave_node_name)
            }
            stage("Store TestRail reports to job description") {
                def String description = readFile("description.txt")
                currentBuild.description += "\n${description}"
            }
        }
    }
  }
//}