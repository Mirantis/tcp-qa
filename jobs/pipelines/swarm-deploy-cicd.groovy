/**
 *
 * Deploy CICD cluster using Jenkins master on cfg01 node
 *
 * Expected parameters:

 *   PARENT_NODE_NAME              Name of the jenkins slave to create the environment
 *   PARENT_WORKSPACE              Path to the workspace of the parent job to use tcp-qa repo
 *   ENV_NAME                      Fuel-devops environment name
 *   STACK_INSTALL                 Stacks to install using Jenkins on cfg01 node: "core,cicd"
 *   STACK_INSTALL_TIMEOUT         Stacks installation timeout
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 *   SHUTDOWN_ENV_ON_TEARDOWN      optional, shutdown fuel-devops environment at the end of the job
 *   MAKE_SNAPSHOT_STAGES          optional, use "dos.py snapshot" to snapshot stages
 *
 */

@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()
make_snapshot_stages = "${env.MAKE_SNAPSHOT_STAGES}" != "false" ? true : false

if (! env.PARENT_NODE_NAME) {
    error "'PARENT_NODE_NAME' must be set from the parent deployment job!"
}

currentBuild.description = "${PARENT_NODE_NAME}:${ENV_NAME}"

def install_timeout = env.STACK_INSTALL_TIMEOUT.toInteger()

timeout(time: install_timeout + 600, unit: 'SECONDS') {

    node ("${PARENT_NODE_NAME}") {
        if (! fileExists("${PARENT_WORKSPACE}")) {
            error "'PARENT_WORKSPACE' contains path to non-existing directory ${PARENT_WORKSPACE} on the node '${PARENT_NODE_NAME}'."
        }
        dir("${PARENT_WORKSPACE}") {

            if (! env.STACK_INSTALL) {
                error "'STACK_INSTALL' must contain one or more comma separated stack names for [deploy_openstack] pipeline"
            }

            if (env.TCP_QA_REFS) {
                stage("Update working dir to patch ${TCP_QA_REFS}") {
                    shared.update_working_dir()
                }
            }

            try {
                // Install core and cicd
                stage("Run Jenkins job on salt-master [deploy_openstack:${env.STACK_INSTALL}]") {
                    shared.run_job_on_day01_node(env.STACK_INSTALL, install_timeout)
                }

                for (stack in "${env.STACK_INSTALL}".split(",")) {
                    stage("Sanity check the deployed component [${stack}]") {
                        shared.sanity_check_component(stack)

                        // If oslo_config INI file ${ENV_NAME}_salt_deployed.ini exists,
                        // then make a copy for the created snapshot to allow the system
                        // tests to revert this snapshot along with the metadata from the INI file.
                        shared.run_cmd("""\
                            if [ -f \$(pwd)/${ENV_NAME}_salt_deployed.ini ]; then
                                cp \$(pwd)/${ENV_NAME}_salt_deployed.ini \$(pwd)/${ENV_NAME}_${stack}_deployed.ini
                            fi
                        """)
                    }
                } // for

                if (make_snapshot_stages) {
                    stage("Make environment snapshots for [${env.STACK_INSTALL}]") {
                        shared.devops_snapshot(env.STACK_INSTALL)
                    }
                }

            } catch (e) {
                common.printMsg("Job is failed", "purple")
                shared.download_logs("deploy_drivetrain_${ENV_NAME}")
                throw e
            } finally {
                // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
                // and report appropriate data to TestRail
                // TODO(ddmitriev): add checks for cicd cluster
                if (make_snapshot_stages) {
                    if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
                        shared.run_cmd("""\
                            dos.py destroy ${ENV_NAME}
                        """)
                    }
                }
            }

        } // dir
    } // node
}