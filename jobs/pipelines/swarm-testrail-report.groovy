/**
 *
 * Deploy the product cluster using Jenkins master on CICD cluster
 *
 * Expected parameters:

 *   ENV_NAME                      Fuel-devops environment name
 *   MCP_VERSION                   MCP version, like 2018.4 or proposed
 *   PASSED_STEPS                  Steps passed to install components using Jenkins on CICD cluster: "salt,core,cicd,openstack:3200,stacklight:2400",
                                   where 3200 and 2400 might be timeouts (not used in the testing pipeline)
 *   PARENT_NODE_NAME              Name of the jenkins slave to create the environment
 *   PARENT_WORKSPACE              Path to the workspace of the parent job to use tcp-qa repo
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 */

@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()
def stacks = shared.get_steps_list(PASSED_STEPS)

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

            if (env.TCP_QA_REFS) {
                stage("Update working dir to patch ${TCP_QA_REFS}") {
                    shared.update_working_dir()
                }
            }

            def report_name = ''
            def testSuiteName = ''
            def methodname = ''
            def testrail_name_template = ''
            def reporter_extra_options = []

            stage("Archive all xml reports") {
                archiveArtifacts artifacts: "**/*.xml"
            }

            def deployment_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"deployment_${ENV_NAME}.xml\"", returnStdout: true)
            def tcpqa_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"nosetests.xml\"", returnStdout: true)
            def tempest_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"report_*.xml\"", returnStdout: true)
            def k8s_conformance_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"conformance_result.xml\"", returnStdout: true)
            def stacklight_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"stacklight_report.xml\"", returnStdout: true)
            common.printMsg(deployment_report_name ? "Found deployment report: ${deployment_report_name}" : "Deployment report not found", deployment_report_name ? "blue" : "red")
            common.printMsg(tcpqa_report_name ? "Found tcp-qa report: ${tcpqa_report_name}" : "tcp-qa report not found", tcpqa_report_name ? "blue" : "red")
            common.printMsg(tempest_report_name ? "Found tempest report: ${tempest_report_name}" : "tempest report not found", tempest_report_name ? "blue" : "red")
            common.printMsg(k8s_conformance_report_name ? "Found k8s conformance report: ${k8s_conformance_report_name}" : "k8s conformance report not found", k8s_conformance_report_name ? "blue" : "red")
            common.printMsg(stacklight_report_name ? "Found stacklight-pytest report: ${stacklight_report_name}" : "stacklight-pytest report not found", stacklight_report_name ? "blue" : "red")


            if (deployment_report_name) {
                stage("Deployment report") {
//                    report_name = "deployment_${ENV_NAME}.xml"
                    testSuiteName = "[MCP] Integration automation"
                    methodname = '{methodname}'
                    testrail_name_template = '{title}'
                    reporter_extra_options = [
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'All\'",
                    ]
                    shared.upload_results_to_testrail(deployment_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                }
            }

            if (tcpqa_report_name) {
                stage("tcp-qa cases report") {
                    // tcpqa_report_name =~ "nosetests.xml"
                    testSuiteName = "[MCP_X] integration cases"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    reporter_extra_options = [
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'All\'",
                    ]
                    shared.upload_results_to_testrail(tcpqa_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                }
            }

            if ('openstack' in stacks && tempest_report_name) {
                stage("Tempest report") {
                    // tempest_report_name =~ "report_*.xml"
                    testSuiteName = "[MCP1.1_PIKE]Tempest"
                    methodname = "{classname}.{methodname}"
                    testrail_name_template = "{title}"
                    shared.upload_results_to_testrail(tempest_report_name, testSuiteName, methodname, testrail_name_template)
                }
            }

            if ('k8s' in stacks && k8s_conformance_report_name) {
                stage("K8s conformance report") {
                    // k8s_conformance_report_name =~ conformance_result.xml
                    // TODO(ddmitriev): it's better to get the k8s version right after deployment
                    // and store in some artifact that can be re-used here.
                    def k8s_version=shared.run_cmd_stdout("""\
                        . ./env_k8s_version;
                        echo "\$KUBE_SERVER_VERSION"
                    """).trim().split().last()
                    testSuiteName = "[MCP][k8s]Hyperkube ${k8s_version}.x"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    reporter_extra_options = [
                      "--send-duplicates",
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'Conformance\'",
                    ]
                    shared.upload_results_to_testrail(k8s_conformance_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                }
            }

            if ('stacklight' in stacks && stacklight_report_name) {
                stage("stacklight-pytest report") {
                    // stacklight_report_name =~ "stacklight_report.xml"
                    testSuiteName = "LMA2.0_Automated"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    shared.upload_results_to_testrail(stacklight_report_name, testSuiteName, methodname, testrail_name_template)
                }
            }

        } catch (e) {
            common.printMsg("Job is failed", "purple")
            throw e
        } finally {
            // reporting is failed for some reason
        }
    }
}
