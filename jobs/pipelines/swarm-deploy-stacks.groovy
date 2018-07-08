/**
 *
 * Deploy the product cluster using Jenkins master on CICD cluster
 *
 * Expected parameters:

 *   NODE_NAME                     Name of the jenkins slave to create the environment
 *   ENV_NAME                      Fuel-devops environment name
 *   STACK_INSTALL                 Stacks to install using Jenkins on CICD cluster: "openstack:3200,stacklight:2400", where 3200 and 2400 are timeouts
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 *   SHUTDOWN_ENV_ON_TEARDOWN      optional, shutdown fuel-devops environment at the end of the job
 *
 */

@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()


node ("${NODE_NAME}") {
  try {

    if (! env.STACK_INSTALL) {
        error "'STACK_INSTALL' must contain one or more comma separated stack names for [deploy_openstack] pipeline"
    }

    stage("Clean the environment and clone tcp-qa") {
        shared.prepare_working_dir()
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
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
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
