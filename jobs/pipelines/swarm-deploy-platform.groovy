/**
 *
 * Deploy the product cluster using Jenkins master on CICD cluster
 *
 * Expected parameters:

 *   PARENT_NODE_NAME              Name of the jenkins slave to create the environment
 *   PARENT_WORKSPACE              Path to the workspace of the parent job to use tcp-qa repo
 *   ENV_NAME                      Fuel-devops environment name
 *   STACK_INSTALL                 Stacks to install using Jenkins on CICD cluster: "openstack:3200,stacklight:2400", where 3200 and 2400 are timeouts
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 *   SHUTDOWN_ENV_ON_TEARDOWN      optional, shutdown fuel-devops environment at the end of the job
 *
 */

@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()

if (! env.PARENT_NODE_NAME) {
    error "'PARENT_NODE_NAME' must be set from the parent deployment job!"
}

currentBuild.description = "${PARENT_NODE_NAME}:${ENV_NAME}"

node ("${PARENT_NODE_NAME}") {
    if (! fileExists("${PARENT_WORKSPACE}")) {
        error "'PARENT_WORKSPACE' contains path to non-existing directory ${PARENT_WORKSPACE} on the node '${PARENT_NODE_NAME}'."
    }
    dir("${PARENT_WORKSPACE}") {
        try {

            if (! env.STACK_INSTALL) {
                error "'STACK_INSTALL' must contain one or more comma separated stack names for [deploy_openstack] pipeline"
            }

            if (env.TCP_QA_REFS) {
                stage("Update working dir to patch ${TCP_QA_REFS}") {
                    shared.update_working_dir()
                }
            }

            // Install the cluster
            def stack
            def timeout

            for (element in "${STACK_INSTALL}".split(",")) {
                if (element.contains(':')) {
                    (stack, timeout) = element.split(':')
                } else {
                    stack = element
                    timeout = '1800'
                }
                stage("Run Jenkins job on CICD [deploy_openstack:${stack}]") {
                    shared.run_job_on_cicd_nodes(stack, timeout)
                }

                stage("Sanity check the deployed component [${stack}]") {
                    shared.sanity_check_component(stack)
                }

                stage("Make environment snapshot [${stack}_deployed]") {
                    shared.devops_snapshot(stack)
                }
            }

        } catch (e) {
            common.printMsg("Job is failed", "purple")
            throw e
        } finally {
            // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
            // and report appropriate data to TestRail
            // TODO(ddmitriev): add checks for the installed stacks
            if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
                shared.run_cmd("""\
                    dos.py destroy ${ENV_NAME}
                """)
            }
        }
    }
}
