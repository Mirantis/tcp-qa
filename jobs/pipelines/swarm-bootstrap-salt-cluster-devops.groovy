/**
 *
 * Create fuel-devops environment, generate a model for it
 * and bootstrap a salt cluster on the environment nodes
 *
 * Expected parameters:

 *   NODE_NAME                     Name of the jenkins slave to create the environment
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
 *
 */

@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()

// Helper pipeline, to create a fuel-devops environment
// and generate the model based on the environment parameters.

node ("${NODE_NAME}") {
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
        // do not fail if environment doesn't exists
        shared.run_cmd("""\
        python ./tcp_tests/utils/create_devops_env.py
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
        virsh vol-upload ${ENV_NAME}_cfg01.${LAB_CONFIG_NAME}.local_config /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} --pool default
        virsh pool-refresh --pool default
        """)
    }

    stage("Run the 'underlay' and 'salt-deployed' fixtures to bootstrap salt cluster") {
        shared.run_cmd("""\
        export MANAGER=devops
        export SHUTDOWN_ENV_ON_TEARDOWN=false
        export BOOTSTRAP_TIMEOUT=900
        export PYTHONIOENCODING=UTF-8
        export REPOSITORY_SUITE=${MCP_VERSION}
        #export SALT_STEPS_PATH=templates/${LAB_CONFIG_NAME}/salt.yaml
        export TEST_GROUP=test_install_local_salt
        py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -k \${TEST_GROUP}
        sleep 60  # wait for jenkins to start and IO calm down

        """)
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
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