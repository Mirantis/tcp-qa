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
 *   OS_USER_DOMAIN_NAME           OpenStack user domain name
 *   OS_CREDENTIALS                OpenStack username and password credentials ID in Jenkins
 *   LAB_PARAM_DEFAULTS            Filename placed in tcp_tests/templates/_heat_environments, with default parameters for the heat template
 *
 *   CREATE_JENKINS_NODE_CREDENTIALS   Jenkins username and password with rights to add/delete Jenkins agents
 */

@Library('tcp-qa')_

import groovy.xml.XmlUtil

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()

if (! env.PARENT_NODE_NAME) {
    error "'PARENT_NODE_NAME' must be set from the parent deployment job!"
}

currentBuild.description = "${PARENT_NODE_NAME}:${ENV_NAME}"
def cfg01_day01_image_name = "cfg01-day01-${MCP_VERSION}"
def ubuntu_vcp_image_name = "ubuntu-vcp-${MCP_VERSION}"
def ubuntu_foundation_image_name = "ubuntu-16.04-foundation-${MCP_VERSION}"

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
            env.OS_IDENTITY_API_VERSION = 3

            stage("Cleanup: erase ${ENV_NAME} and remove config drive") {

                // delete heat stack
                println "Remove heat stack '${ENV_NAME}'"
                shared.run_cmd("""\
                    # export OS_IDENTITY_API_VERSION=3
                    # export OS_AUTH_URL=${OS_AUTH_URL}
                    # export OS_USERNAME=${OS_USERNAME}
                    # export OS_PASSWORD=${OS_PASSWORD}
                    # export OS_PROJECT_NAME=${OS_PROJECT_NAME}
                    openstack --insecure stack delete -y ${ENV_NAME} || true
                    while openstack --insecure stack show ${ENV_NAME} -f value -c stack_status; do sleep 10; done
                """)

                println "Remove config drive ISO"
                shared.run_cmd("""\
                    rm /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} || true
                """)
            }

            stage("Generate the model") {
                def IPV4_NET_ADMIN=shared.run_cmd_stdout("./tcp_tests/utils/get_param_heat_template.py management_subnet_cidr").trim().split().last()
                def IPV4_NET_CONTROL=shared.run_cmd_stdout("./tcp_tests/utils/get_param_heat_template.py control_subnet_cidr").trim().split().last()
                def IPV4_NET_TENANT=shared.run_cmd_stdout("./tcp_tests/utils/get_param_heat_template.py tenant_subnet_cidr").trim().split().last()
                def IPV4_NET_EXTERNAL=shared.run_cmd_stdout("./tcp_tests/utils/get_param_heat_template.py external_subnet_cidr").trim().split().last()
                shared.generate_cookied_model(IPV4_NET_ADMIN, IPV4_NET_CONTROL, IPV4_NET_TENANT, IPV4_NET_EXTERNAL)
            }

            stage("Generate config drive ISO") {
                SALT_MASTER_IP=shared.run_cmd_stdout("./tcp_tests/utils/get_param_heat_template.py management_subnet_cfg01_ip").trim().split().last()
                def ADMIN_NETWORK_GW=shared.run_cmd_stdout("./tcp_tests/utils/get_param_heat_template.py management_subnet_gateway_ip").trim().split().last()
                shared.generate_configdrive_iso(SALT_MASTER_IP, ADMIN_NETWORK_GW)
            }

            stage("Upload Ubuntu image for foundation node") {
                shared.run_cmd("""\
                    if ! openstack --insecure image show ${ubuntu_foundation_image_name} -f value -c name; then
                        wget -O ./${ubuntu_foundation_image_name} https://cloud-images.ubuntu.com/releases/16.04/release/ubuntu-16.04-server-cloudimg-amd64-disk1.img
                        openstack --insecure image create ${ubuntu_foundation_image_name} --file ./${ubuntu_foundation_image_name} --disk-format qcow2 --container-format bare
                        rm ./${ubuntu_foundation_image_name}
                    else
                        echo Image ${ubuntu_foundation_image_name} already exists
                    fi
                """)
            }

            stage("Upload cfg01-day01 and VCP images") {
                shared.run_cmd("""\
                    # export OS_IDENTITY_API_VERSION=3
                    # export OS_AUTH_URL=${OS_AUTH_URL}
                    # export OS_USERNAME=${OS_USERNAME}
                    # export OS_PASSWORD=${OS_PASSWORD}
                    # export OS_PROJECT_NAME=${OS_PROJECT_NAME}

                    openstack --insecure image show ${cfg01_day01_image_name} -f value -c name || openstack --insecure image create ${cfg01_day01_image_name} --file ${IMAGE_PATH_CFG01_DAY01} --disk-format qcow2 --container-format bare
                    openstack --insecure image show ${ubuntu_vcp_image_name} -f value -c name || openstack --insecure image create ${ubuntu_vcp_image_name} --file ${MCP_IMAGE_PATH1604} --disk-format qcow2 --container-format bare
                """)
            }

            stage("Upload generated config drive ISO into volume on cfg01 node") {
                shared.run_cmd("""\
                    # export OS_IDENTITY_API_VERSION=3
                    # export OS_AUTH_URL=${OS_AUTH_URL}
                    # export OS_USERNAME=${OS_USERNAME}
                    # export OS_PASSWORD=${OS_PASSWORD}
                    # export OS_PROJECT_NAME=${OS_PROJECT_NAME}

                    openstack --insecure image delete cfg01.${ENV_NAME}-config-drive.iso || true
                    sleep 3
                    openstack --insecure image create cfg01.${ENV_NAME}-config-drive.iso --file /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} --disk-format iso --container-format bare
                """)
            }

            stage("Create Heat stack '${ENV_NAME}'") {
                // Create stack and wait for CREATE_COMPLETED status, manual analog:
                //    openstack --insecure stack create ${ENV_NAME} \
                //        --template ./tcp_tests/templates/${LAB_CONFIG_NAME}/underlay.hot \
                //        --environment ./tcp_tests/templates/_heat_environments/${LAB_PARAM_DEFAULTS} \
                //        --parameter env_name=${ENV_NAME} --parameter mcp_version=${MCP_VERSION}
                shared.run_cmd("""\
                    export BOOTSTRAP_TIMEOUT=3600
                    export ENV_MANAGER=heat
                    export TEST_GROUP=test_create_environment
                    export SHUTDOWN_ENV_ON_TEARDOWN=false
                    export PYTHONIOENCODING=UTF-8
                    export REPOSITORY_SUITE=${MCP_VERSION}
                    export ENV_NAME=${ENV_NAME}
                    export LAB_CONFIG_NAME=${LAB_CONFIG_NAME}
                    export LAB_PARAM_DEFAULTS=${LAB_PARAM_DEFAULTS}
                    export LOG_NAME=swarm_test_create_environment.log
                    py.test --cache-clear -vvv -s -p no:django -p no:ipdb --junit-xml=deploy_hardware.xml -k \${TEST_GROUP}
                """)
            }

            stage("Add the Jenkins slave node") {
                def jenkins_slave_ip_value_name = "foundation_floating"
                def jenkins_slave_ip = shared.run_cmd_stdout("openstack --insecure stack output show ${ENV_NAME} ${jenkins_slave_ip_value_name} -f value -c output_value").trim().split().last()
                def jenkins_slave_executors = 2
                common.printMsg("JENKINS_SLAVE_NODE_NAME=${JENKINS_SLAVE_NODE_NAME}", "green")
                common.printMsg("JENKINS_SLAVE_IP=${jenkins_slave_ip}", "green")

        withCredentials([
           [$class          : 'UsernamePasswordMultiBinding',
           credentialsId   : "${CREATE_JENKINS_NODE_CREDENTIALS}",
           passwordVariable: 'JENKINS_PASS',
           usernameVariable: 'JENKINS_USER']
        ]) {

                script_delete_agent = ("""\
                    CRUMB=\$(curl --fail -0 -u \"\${JENKINS_USER}:\${JENKINS_PASS}\" \${JENKINS_URL}\'/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,":",//crumb)\' 2>/dev/null)
                    curl -w '%{http_code}' -o /dev/null \
                        -u \"\${JENKINS_USER}:\${JENKINS_PASS}\" \
                        -H \"Content-Type:application/x-www-form-urlencoded\" \
                        -H \"\$CRUMB\" \
                        \"\${JENKINS_URL}/computer/\${JENKINS_SLAVE_NODE_NAME}/doDelete\" \
                        --request \'POST\' --data \'\'
                    sleep 10
                """)

                script_create_agent = ("""\
                    CRUMB=\$(curl --fail -0 -u \"\${JENKINS_USER}:\${JENKINS_PASS}\" \${JENKINS_URL}\'/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,":",//crumb)\' 2>/dev/null)

                    curl -L -sS -w '%{http_code}' -o /dev/null \
                        -u \"\${JENKINS_USER}:\${JENKINS_PASS}\" \
                        -H \"Content-Type:application/x-www-form-urlencoded\" \
                        -H \"\$CRUMB\" \
                        -X POST -d 'json={\
                            \"name\": \"'\"\$JENKINS_SLAVE_NODE_NAME\"'\", \
                            \"nodeDescription\": \"'\"\$ENV_NAME\"'\", \
                            \"numExecutors\": \"'\"${jenkins_slave_executors}\"'\", \
                            \"remoteFS\": \"'\"/home/jenkins/workspace\"'\", \
                            \"labelString\": \"'\"\$ENV_NAME\"'\", \
                            \"mode\": \"EXCLUSIVE\", \
                            \"\": [\"hudson.plugins.sshslaves.SSHLauncher\", \"hudson.slaves.RetentionStrategy\$Always\"], \
                            \"launcher\": {\
                                \"stapler-class\": \"hudson.plugins.sshslaves.SSHLauncher\", \
                                \"\$class\": \"hudson.plugins.sshslaves.SSHLauncher\", \
                                \"host\": \"'\"${jenkins_slave_ip}\"'\", \
                                \"credentialsId\": \"'\"\$ACCESS_JENKINS_NODE_CREDENTIALS\"'\", \
                                \"port\": \"'\"22\"'\", \
                                \"javaPath\": \"\", \
                                \"jvmOptions\": \"\", \
                                \"prefixStartSlaveCmd\": \"\", \
                                \"suffixStartSlaveCmd\": \"\", \
                                \"launchTimeoutSeconds\": \"\", \
                                \"maxNumRetries\": \"\", \
                                \"retryWaitTime\": \"\", \
                                \"sshHostKeyVerificationStrategy\": {\
                                    \"\$class\": \"hudson.plugins.sshslaves.verifiers.NonVerifyingKeyVerificationStrategy\" \
                                }, \
                                \"tcpNoDelay\": \"true\"\
                            }, \
                            \"retentionStrategy\": {\
                                \"stapler-class\": \"hudson.slaves.RetentionStrategy\$Always\", \
                                \"\$class\": \"hudson.slaves.RetentionStrategy\$Always\"\
                            }, \
                            \"nodeProperties\": {\
                                \"stapler-class-bag\": \"true\"\
                            }, \
                            \"type\": \"hudson.slaves.DumbSlave\", \
                            \"crumb\": \"'\"\$CRUMB\"'\"}' \
                        \"\${JENKINS_URL}/computer/doCreateItem?name=\${JENKINS_SLAVE_NODE_NAME}&type=hudson.slaves.DumbSlave\"
                """)
                shared.verbose_sh(script_delete_agent, true, false, true)
                shared.verbose_sh(script_create_agent, true, false, true)

                // Store jenkins agent IP address
                jenkins_agent_description = "ssh jenkins@${jenkins_slave_ip}  # foundation node with Jenkins agent <a href=${JENKINS_URL}/computer/${JENKINS_SLAVE_NODE_NAME}>${JENKINS_SLAVE_NODE_NAME}</a><br>ssh root@${SALT_MASTER_IP}  # cfg01 node<br>"
                writeFile(file: "jenkins_agent_description.txt", text: jenkins_agent_description, encoding: "UTF-8")

        } // withCredentials

            }// stage

        } // withCredentials

    } // dir
} // node


node ("${JENKINS_SLAVE_NODE_NAME}") {
    dir("${PARENT_WORKSPACE}") {

        stage("Clean the environment and clone tcp-qa") {
            deleteDir()
            shared.verbose_sh("""\
                [ -d /home/jenkins/venv_testrail_reporter ] || virtualenv /home/jenkins/venv_testrail_reporter
            """, true, false, true)
            shared.run_cmd("""\
                . /home/jenkins/venv_testrail_reporter/bin/activate; pip install git+https://github.com/dis-xcom/testrail_reporter -U  ${PARENT_WORKSPACE}
            """)
            shared.verbose_sh("""\
                [ -d /home/jenkins/fuel-devops30 ] || virtualenv /home/jenkins/fuel-devops30
            """, true, false, true)
            shared.run_cmd("""\
                git clone https://github.com/Mirantis/tcp-qa.git ${PARENT_WORKSPACE}
            """)
            shared.update_working_dir()
        }

        withCredentials([
           [$class          : 'UsernamePasswordMultiBinding',
           credentialsId   : env.OS_CREDENTIALS,
           passwordVariable: 'OS_PASSWORD',
           usernameVariable: 'OS_USERNAME']
        ]) {


            stage("Run the 'underlay' and 'salt-deployed' fixtures to bootstrap salt cluster") {
                def xml_report_name = "deploy_salt.xml"
                try {
                    // deploy_salt.xml
                    shared.run_sh("""\
                        export ENV_NAME=${ENV_NAME}
                        export LAB_CONFIG_NAME=${LAB_CONFIG_NAME}
                        export LAB_PARAM_DEFAULTS=${LAB_PARAM_DEFAULTS}
                        export ENV_MANAGER=heat
                        export SHUTDOWN_ENV_ON_TEARDOWN=false
                        export BOOTSTRAP_TIMEOUT=3600
                        export PYTHONIOENCODING=UTF-8
                        export REPOSITORY_SUITE=${MCP_VERSION}
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
                    // TODO(ddmitriev): add checks for salt cluster
                }
            } // stage
        } // withCredentials
    } // dir
} // node
