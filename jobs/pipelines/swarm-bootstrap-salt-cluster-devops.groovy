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
                export ENV_MANAGER=devops
                export PYTHONIOENCODING=UTF-8
                export REPOSITORY_SUITE=${MCP_VERSION}
                export TEST_GROUP=test_create_environment
                export LOG_NAME=swarm_test_create_environment.log
                py.test -vvv -s -p no:django -p no:ipdb --junit-xml=deploy_hardware.xml -k \${TEST_GROUP}
            """)
        }

        stage("Generate the model") {
            def IPV4_NET_ADMIN=shared.run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep admin-pool01").trim().split().last()
            def IPV4_NET_CONTROL=shared.run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep private-pool01").trim().split().last()
            def IPV4_NET_TENANT=shared.run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep tenant-pool01").trim().split().last()
            def IPV4_NET_EXTERNAL=shared.run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep external-pool01").trim().split().last()
            shared.generate_cookied_model(IPV4_NET_ADMIN, IPV4_NET_CONTROL, IPV4_NET_TENANT, IPV4_NET_EXTERNAL)
        }

        stage("Generate config drive ISO") {
            def SALT_MASTER_IP=shared.run_cmd_stdout("""\
                SALT_MASTER_INFO=\$(for node in \$(dos.py slave-ip-list --address-pool-name admin-pool01 ${ENV_NAME}); do echo \$node; done|grep cfg01)
                echo \$SALT_MASTER_INFO|cut -d',' -f2
                """).trim().split("\n").last()
            def dhcp_ranges_json=shared.run_cmd_stdout("""\
                fgrep dhcp_ranges ${ENV_NAME}_hardware.ini |
                fgrep "admin-pool01"|
                cut -d"=" -f2
                """).trim().split("\n").last()
            def dhcp_ranges = new groovy.json.JsonSlurperClassic().parseText(dhcp_ranges_json)
            def ADMIN_NETWORK_GW = dhcp_ranges['admin-pool01']['gateway']
            shared.generate_configdrive_iso(SALT_MASTER_IP, ADMIN_NETWORK_GW)
        }

        stage("Upload generated config drive ISO into volume on cfg01 node") {
            def SALT_MASTER_HOSTNAME=shared.run_cmd_stdout("""\
                SALT_MASTER_INFO=\$(for node in \$(dos.py slave-ip-list --address-pool-name admin-pool01 ${ENV_NAME}); do echo \$node; done|grep cfg01)
                echo \$SALT_MASTER_INFO|cut -d',' -f1
                """).trim().split("\n").last()
            shared.run_cmd("""\
                # Get SALT_MASTER_HOSTNAME to determine the volume name
                virsh vol-upload ${ENV_NAME}_${SALT_MASTER_HOSTNAME}_config /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} --pool default
                virsh pool-refresh --pool default
            """)
        }

        stage("Run the 'underlay' and 'salt-deployed' fixtures to bootstrap salt cluster") {
            def xml_report_name = "deploy_salt.xml"
            try {
                // deploy_salt.xml
                shared.run_sh("""\
                    export ENV_NAME=${ENV_NAME}
                    export LAB_CONFIG_NAME=${LAB_CONFIG_NAME}
                    export ENV_MANAGER=devops
                    export SHUTDOWN_ENV_ON_TEARDOWN=false
                    export BOOTSTRAP_TIMEOUT=1800
                    export PYTHONIOENCODING=UTF-8
                    export REPOSITORY_SUITE=${MCP_VERSION}
                    export JENKINS_PIPELINE_BRANCH=${JENKINS_PIPELINE_BRANCH}
                    export TEST_GROUP=test_bootstrap_salt
                    export LOG_NAME=swarm_test_bootstrap_salt.log
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
}