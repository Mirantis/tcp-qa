/**
 *
 * Create fuel-devops environment, generate a model for it
 * and bootstrap a salt cluster on the environment nodes
 *
 * Expected parameters:

 *   PARENT_NODE_NAME              Name of the jenkins slave to create the environment
 *   PARENT_WORKSPACE              Path to the workspace of the parent job to use tcp-qa repo
 *   LAB_CONFIG_NAME               Name of the tcp-qa deployment template
 *   ENV_NAME                      Fuel-devops environment name
 *   MCP_VERSION                   MCP version, like 2018.4 or proposed
 *   MCP_IMAGE_PATH1604            Local path to the image http://ci.mcp.mirantis.net:8085/images/ubuntu-16-04-x64-mcpproposed.qcow2
 *   IMAGE_PATH_CFG01_DAY01        Local path to the image http://ci.mcp.mirantis.net:8085/images/cfg01-day01-proposed.qcow2
 *   CFG01_CONFIG_IMAGE_NAME       Name for the creating config drive image, like cfg01.${LAB_CONFIG_NAME}-config-drive.iso
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 *   PIPELINE_LIBRARY_REF          Reference to the pipeline-library change
 *   MK_PIPELINES_REF              Reference to the mk-pipelines change
 *   COOKIECUTTER_TEMPLATE_COMMIT  Commit/tag/branch for cookiecutter-templates repository. If empty, then takes ${MCP_VERSION} value
 *   SALT_MODELS_SYSTEM_COMMIT     Commit/tag/branch for reclass-system repository. If empty, then takes ${MCP_VERSION} value
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
            stage("Cleanup: erase ${ENV_NAME} and remove config drive") {
                println "Remove environment ${ENV_NAME}"
                shared.run_cmd("""\
                    dos.py erase ${ENV_NAME} || true
                """)
                println "Remove config drive ISO"
                shared.run_cmd("""\
                    rm /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} || true
                """)
            }

            stage("Create an environment ${ENV_NAME} in disabled state") {
                // deploy_hardware.xml
                shared.run_cmd("""\
                    export ENV_NAME=${ENV_NAME}
                    export LAB_CONFIG_NAME=${LAB_CONFIG_NAME}
                    export MANAGER=devops
                    export PYTHONIOENCODING=UTF-8
                    export REPOSITORY_SUITE=${MCP_VERSION}
                    export TEST_GROUP=test_create_environment
                    py.test -vvv -s -p no:django -p no:ipdb --junit-xml=deploy_hardware.xml -k \${TEST_GROUP}
                """)
            }

            stage("Generate the model") {
                shared.generate_cookied_model()
            }

            stage("Generate config drive ISO") {
                shared.generate_configdrive_iso()
            }

            stage("Upload generated config drive ISO into volume on cfg01 node") {
                shared.run_cmd("""\
                    # Get SALT_MASTER_HOSTNAME to determine the volume name
                    . ./tcp_tests/utils/env_salt
                    virsh vol-upload ${ENV_NAME}_\${SALT_MASTER_HOSTNAME}_config /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} --pool default
                    virsh pool-refresh --pool default
                """)
            }

            stage("Run the 'underlay' and 'salt-deployed' fixtures to bootstrap salt cluster") {
                // deploy_salt.xml
                shared.run_cmd("""\
                    export ENV_NAME=${ENV_NAME}
                    export LAB_CONFIG_NAME=${LAB_CONFIG_NAME}
                    export MANAGER=devops
                    export SHUTDOWN_ENV_ON_TEARDOWN=false
                    export BOOTSTRAP_TIMEOUT=900
                    export PYTHONIOENCODING=UTF-8
                    export REPOSITORY_SUITE=${MCP_VERSION}
                    export TEST_GROUP=test_bootstrap_salt
                    py.test -vvv -s -p no:django -p no:ipdb --junit-xml=deploy_salt.xml -k \${TEST_GROUP}
                    sleep 60  # wait for jenkins to start and IO calm down
                """)
            }

          } catch (e) {
              common.printMsg("Job is failed: " + e.message, "red")
              throw e
          } finally {
            // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
            // and report appropriate data to TestRail
            // TODO(ddmitriev): add checks for salt cluster
            if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
                shared.run_cmd("""\
                    dos.py destroy ${ENV_NAME}
                """)
            }
        }
    }
}