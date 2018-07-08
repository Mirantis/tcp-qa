/**
 *
 * Deploy CICD cluster using Jenkins master on cfg01 node
 *
 * Expected parameters:

 *   NODE_NAME                     Name of the jenkins slave to create the environment
 *   ENV_NAME                      Fuel-devops environment name
 *   STACK_INSTALL                 Stacks to install using Jenkins on cfg01 node
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 *   SHUTDOWN_ENV_ON_TEARDOWN      optional, shutdown fuel-devops environment at the end of the job
 *
 */

@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()


node ("${NODE_NAME}") {
  try {

    stage("Clean the environment and clone tcp-qa") {
        shared.prepare_working_dir()
    }
    // Install core and cicd
    for (stack in "${STACK_INSTALL}".split(",")) {
        stage("Run Jenkins job on salt-master [deploy_openstack:${stack}]") {
            shared.run_job_on_day01_node(stack)
        }
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
      throw e
  } finally {
    // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
    // and report appropriate data to TestRail
    // TODO(ddmitriev): add checks for cicd cluster
    if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
        shared.run_cmd("""\
            dos.py destroy ${ENV_NAME}
        """)
    }
  }
}
