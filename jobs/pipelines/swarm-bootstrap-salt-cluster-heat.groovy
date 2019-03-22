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
 *   MCP_SALT_REPO_URL             Base URL for MCP repositories required to bootstrap cfg01 node. Leave blank to use default
 *                                 (http://mirror.mirantis.com/ from mcp-common-scripts)
 *   MCP_SALT_REPO_KEY             URL of the key file. Leave blank to use default
 *                                 (${MCP_SALT_REPO_URL}/${MCP_VERSION}/salt-formulas/xenial/archive-salt-formulas.key from mcp-common-scripts)
 *   OS_AUTH_URL                   OpenStack keystone catalog URL
 *   OS_PROJECT_NAME               OpenStack project (tenant) name
 *   OS_CREDENTIALS                OpenStack username and password credentials ID in Jenkins
 *
 */

@Library('tcp-qa')_

import groovy.xml.XmlUtil

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

        if (env.TCP_QA_REFS) {
            stage("Update working dir to patch ${TCP_QA_REFS}") {
                shared.update_working_dir()
            }
        }
        withCredentials([
           [$class          : 'UsernamePasswordMultiBinding',
           credentialsId   : env.OS_CREDENTIALS,
           passwordVariable: 'OS_PASSWORD',
           usernameVariable: 'OS_USERNAME']
        ]) {

            stage("Cleanup: erase ${ENV_NAME} and remove config drive") {

                // delete heat stack
                println "Remove heat stack '${ENV_NAME}'"
                shared.run_cmd("""\
                    export OS_IDENTITY_API_VERSION=3
                    # export OS_AUTH_URL=${OS_AUTH_URL}
                    # export OS_USERNAME=${OS_USERNAME}
                    # export OS_PASSWORD=${OS_PASSWORD}
                    # export OS_PROJECT_NAME=${OS_PROJECT_NAME}
                    openstack stack delete -y ${ENV_NAME}
                    while openstack --insecure stack show ${ENV_NAME} -f value -c stack_status; do sleep 10; done
                """)

                println "Remove config drive ISO"
                shared.run_cmd("""\
                    rm /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} || true
                """)
            }

//// get network IPs
            stage("Generate the model") {
                shared.generate_cookied_model()
            }

            stage("Generate config drive ISO") {
                shared.generate_configdrive_iso()
            }

            stage("Upload cfg01-day01 and VCP images") {
                shared.run_cmd("""\
                    export OS_IDENTITY_API_VERSION=3
                    # export OS_AUTH_URL=${OS_AUTH_URL}
                    # export OS_USERNAME=${OS_USERNAME}
                    # export OS_PASSWORD=${OS_PASSWORD}
                    # export OS_PROJECT_NAME=${OS_PROJECT_NAME}

                    openstack --insecure image show cfg01-day01-${MCP_VERSION}.qcow2 -f value -c name || openstack --insecure image create cfg01-day01-${MCP_VERSION}.qcow2 --file /home/jenkins/images/${IMAGE_PATH_CFG01_DAY01} --disk-format qcow2 --container-format bare
                    openstack --insecure image show ubuntu-vcp-${MCP_VERSION}.qcow2 -f value -c name || openstack --insecure image create ubuntu-vcp-${MCP_VERSION}.qcow2 --file /home/jenkins/images/${MCP_IMAGE_PATH1604} --disk-format qcow2 --container-format bare
                """)
            }

            stage("Upload generated config drive ISO into volume on cfg01 node") {
                shared.run_cmd("""\
                    export OS_IDENTITY_API_VERSION=3
                    # export OS_AUTH_URL=${OS_AUTH_URL}
                    # export OS_USERNAME=${OS_USERNAME}
                    # export OS_PASSWORD=${OS_PASSWORD}
                    # export OS_PROJECT_NAME=${OS_PROJECT_NAME}

                    openstack --insecure image delete cfg01.${ENV_NAME}-config-drive.iso
                    sleep 3
                    openstack --insecure image create cfg01.${ENV_NAME}-config-drive.iso --file /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} --disk-format iso --container-format bare
                """)
            }

            stage("Run the 'underlay' and 'salt-deployed' fixtures to bootstrap salt cluster") {
                def xml_report_name = "deploy_salt.xml"
                try {
                    // deploy_salt.xml
                    shared.run_sh("""\
                        export ENV_NAME=${ENV_NAME}
                        export LAB_CONFIG_NAME=${LAB_CONFIG_NAME}
                        export ENV_MANAGER=heat
                        export SHUTDOWN_ENV_ON_TEARDOWN=false
                        export BOOTSTRAP_TIMEOUT=3600
                        export PYTHONIOENCODING=UTF-8
                        export REPOSITORY_SUITE=${MCP_VERSION}
                        export TEST_GROUP=test_bootstrap_salt
                        py.test -vvv -s -p no:django -p no:ipdb --junit-xml=${xml_report_name} -k \${TEST_GROUP}
                    """)
                    // Wait for jenkins to start and IO calm down
                    sleep(60)

                } catch (e) {
                      common.printMsg("Saltstack cluster deploy is failed", "purple")
                      if (fileExists(xml_report_name)) {
                          shared.download_logs("deploy_salt_${ENV_NAME}")
                          def String junit_report_xml = readFile(xml_report_name)
                          def String junit_report_xml_pretty = new XmlUtil().serialize(junit_report_xml)
                          throw new Exception(junit_report_xml_pretty)
                      } else {
                          throw e
                      }
                } finally {
                    // TODO(ddmitriev): add checks for salt cluster
                }
            } // stage
        } // withCredentials
    } // dir
} // node