@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()
def steps = "hardware,create_model,salt," + env.DRIVETRAIN_STACK_INSTALL + "," + env.PLATFORM_STACK_INSTALL
def env_manager = env.ENV_MANAGER ?: 'devops'

if (env_manager == 'devops') {
    jenkins_slave_node_name = "${NODE_NAME}"
    node_with_reports = "${NODE_NAME}"
    make_snapshot_stages = "${env.MAKE_SNAPSHOT_STAGES}" != "false" ? true : false
} else if (env_manager == 'heat') {
    jenkins_slave_node_name = "openstack_slave_${JOB_NAME}"
    make_snapshot_stages = false
    node_with_reports = jenkins_slave_node_name
}

currentBuild.description = "${NODE_NAME}:${ENV_NAME}<br>"

def deploy(shared, common, steps, env_manager) {
    def report_text = ''
    try {

        stage("Clean the environment and clone tcp-qa") {
            shared.prepare_working_dir(env_manager)
        }

        stage("Create environment, generate model, bootstrap the salt-cluster") {
            // steps: "hardware,create_model,salt"
            if (env_manager == 'devops') {
                shared.swarm_bootstrap_salt_cluster_devops()
            } else if (env_manager == 'heat') {
                // If shared.swarm_bootstrap_salt_cluster_heat() failed,
                // do not schedule shared.swarm_testrail_report() on the non existing Jenkins slave
                shared.swarm_bootstrap_salt_cluster_heat(jenkins_slave_node_name)
                // When the Heat stack created, set jenkins_slave_node_name to the new Jenkins slave
                // disable dos.py snapshots for 'heat' manager
            } else {
                throw new Exception("Unknow env_manager: '${env_manager}'")
            }
        }

        stage("Install core infrastructure and deploy CICD nodes") {
        if (env.DRIVETRAIN_STACK_INSTALL) {
                // steps: env.DRIVETRAIN_STACK_INSTALL
                shared.swarm_deploy_cicd(env.DRIVETRAIN_STACK_INSTALL, env.DRIVETRAIN_STACK_INSTALL_TIMEOUT, jenkins_slave_node_name, make_snapshot_stages)
            } else {
                common.printMsg("DRIVETRAIN_STACK_INSTALL is empty, skipping 'swarm-deploy-cicd' job", "green")
            }
        }

        stage("Deploy platform components") {
            if (env.PLATFORM_STACK_INSTALL) {
                // steps: env.PLATFORM_STACK_INSTALL
                shared.swarm_deploy_platform(env.PLATFORM_STACK_INSTALL, env.PLATFORM_STACK_INSTALL_TIMEOUT, jenkins_slave_node_name, make_snapshot_stages)
            } else {
                common.printMsg("PLATFORM_STACK_INSTALL is empty, skipping 'swarm-deploy-platform' job", "green")
            }
        }

        currentBuild.result = 'SUCCESS'

    } catch (e) {
        common.printMsg("Deploy is failed: " + e.message , "purple")
        report_text = e.message
        if (make_snapshot_stages) {
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

def test(shared, common, steps, env_manager) {
    try {
        stage("Run tests") {
            if (env.RUN_TEST_OPTS) {
                shared.swarm_run_pytest(steps, jenkins_slave_node_name, make_snapshot_stages)
            } else {
                common.printMsg("RUN_TEST_OPTS is empty, skipping 'swarm-run-pytest' job", "green")
            }
        }

    } catch (e) {
        common.printMsg("Tests are failed: " + e.message, "purple")
        if (make_snapshot_stages) {
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
        deploy(shared, common, steps, env_manager)
        // run test stages
        test(shared, common, steps, env_manager)
    } catch (e) {
        common.printMsg("Job is failed: " + e.message, "purple")
        throw e
    } finally {
        if (make_snapshot_stages) {
            // shutdown the environment if required
            if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
                shared.run_cmd("""\
                    dos.py destroy ${ENV_NAME} || true
                """)
            }
        }

        if (fileExists("jenkins_agent_description.txt")) {
            def String jenkins_agent_description = readFile("jenkins_agent_description.txt")
            currentBuild.description += "${jenkins_agent_description}"

            // if there is a separated foundation node on $jenkins_slave_node_name,
            // then archive artifacts also on that node
            if (jenkins_slave_node_name != env.NODE_NAME) {
                node ("${jenkins_slave_node_name}") {
                    stage("Archive all xml reports from node ${jenkins_slave_node_name}") {
                        archiveArtifacts artifacts: "**/*.xml,**/*.ini,**/*.log,**/*.tar.gz"
                    }
                    if ("${env.REPORT_TO_TESTRAIL}" != "false") {
                      stage("report results to testrail") {
                      shared.swarm_testrail_report(steps, node_with_reports)
                    }
                    stage("Store TestRail reports to job description from node ${jenkins_slave_node_name}") {
                    def String description = readFile("description.txt")
                    currentBuild.description += "${description}"
                    }
                    }
                }
            }
        }

        stage("Archive all xml reports") {
            archiveArtifacts artifacts: "**/*.xml,**/*.ini,**/*.log,**/*.tar.gz"
        }
        if ("${env.REPORT_TO_TESTRAIL}" != "false") {
            stage("report results to testrail") {
                shared.swarm_testrail_report(steps, node_with_reports)
            }
            stage("Store TestRail reports to job description") {
                def String description = readFile("description.txt")
                currentBuild.description += "${description}"
            }
        }
    } // try
  } // node


//}