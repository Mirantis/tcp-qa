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
 *   TEMPEST_TEST_SUITE_NAME       Name of tempest suite
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
        def description = ''
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

            def report_result = ''
            def report_url = ''

            //  deployment_report_name = "deployment_${ENV_NAME}.xml"
            def deployment_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"deployment_${ENV_NAME}.xml\" -printf \"'%p'\" ", returnStdout: true).trim()
            // tcpqa_report_name =~ "nosetests.xml"
            def tcpqa_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"nosetests.xml\" -printf \"'%p'\" ", returnStdout: true).trim()
            // tempest_report_name =~ "report_*.xml"
            def tempest_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"report_*.xml\" -printf \"'%p'\" ", returnStdout: true).trim()
            // k8s_conformance_report_name =~ conformance_result.xml
            def k8s_conformance_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"conformance_result.xml\" -printf \"'%p'\" ", returnStdout: true).trim()
            // k8s_conformance_report_name =~ conformance_virtlet_result.xml
            def k8s_conformance_virtlet_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"conformance_virtlet_result.xml\" -printf \"'%p'\" ", returnStdout: true).trim()
            // stacklight_report_name =~ "stacklight_report.xml" or "report.xml"
            def stacklight_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"*report.xml\"", returnStdout: true).trim()
            // cvp_sanity_report_name =~ cvp_sanity_report.xml
            def cvp_sanity_report_name = sh(script: "find ${PARENT_WORKSPACE} -name \"cvp_sanity_results.xml\" -printf \"'%p'\" ", returnStdout: true).trim()
            common.printMsg(deployment_report_name ? "Found deployment report: ${deployment_report_name}" : "Deployment report not found", deployment_report_name ? "blue" : "red")
            common.printMsg(tcpqa_report_name ? "Found tcp-qa report: ${tcpqa_report_name}" : "tcp-qa report not found", tcpqa_report_name ? "blue" : "red")
            common.printMsg(tempest_report_name ? "Found tempest report: ${tempest_report_name}" : "tempest report not found", tempest_report_name ? "blue" : "red")
            common.printMsg(k8s_conformance_report_name ? "Found k8s conformance report: ${k8s_conformance_report_name}" : "k8s conformance report not found", k8s_conformance_report_name ? "blue" : "red")
            common.printMsg(k8s_conformance_virtlet_report_name ? "Found k8s conformance virtlet report: ${k8s_conformance_virtlet_report_name}" : "k8s conformance virtlet report not found", k8s_conformance_virtlet_report_name ? "blue" : "red")
            common.printMsg(stacklight_report_name ? "Found stacklight-pytest report: ${stacklight_report_name}" : "stacklight-pytest report not found", stacklight_report_name ? "blue" : "red")
            common.printMsg(cvp_sanity_report_name ? "Found CVP Sanity report: ${cvp_sanity_report_name}" : "CVP Sanity report not found", cvp_sanity_report_name ? "blue" : "red")


            if (deployment_report_name) {
                stage("Deployment report") {
                    testSuiteName = "[MCP] Integration automation"
                    methodname = '{methodname}'
                    testrail_name_template = '{title}'
                    reporter_extra_options = [
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'All\'",
                    ]
                    report_result = shared.upload_results_to_testrail(deployment_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

            if (tcpqa_report_name) {
                stage("tcp-qa cases report") {
                    testSuiteName = "[MCP_X] integration cases"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    reporter_extra_options = [
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'All\'",
                    ]
                    report_result = shared.upload_results_to_testrail(tcpqa_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

            if ('openstack' in stacks && tempest_report_name) {
                stage("Tempest report") {
                    testSuiteName = env.TEMPEST_TEST_SUITE_NAME
                    methodname = "{classname}.{methodname}"
                    testrail_name_template = "{title}"
                    report_result = shared.upload_results_to_testrail(tempest_report_name, testSuiteName, methodname, testrail_name_template)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

            if ('k8s' in stacks && k8s_conformance_report_name) {
                stage("K8s conformance report") {
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
                    report_result = shared.upload_results_to_testrail(k8s_conformance_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

            if ('k8s' in stacks && k8s_conformance_virtlet_report_name) {
                stage("K8s conformance virtlet report") {
                    testSuiteName = "[k8s] Virtlet"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    reporter_extra_options = [
                      "--send-duplicates",
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'Conformance\'",
                    ]
                    report_result = shared.upload_results_to_testrail(k8s_conformance_virtlet_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

            if ('stacklight' in stacks && stacklight_report_name) {
                stage("stacklight-pytest report") {
                    testSuiteName = "LMA2.0_Automated"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    report_result = shared.upload_results_to_testrail(stacklight_report_name, testSuiteName, methodname, testrail_name_template)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

            if ('cicd' in stacks && cvp_sanity_report_name) {
                stage("CVP Sanity report") {
                    testSuiteName = "[MCP] cvp sanity"
                    methodname = '{methodname}'
                    testrail_name_template = '{title}'
                    reporter_extra_options = [
                      "--send-duplicates",
                      "--testrail-add-missing-cases",
                      "--testrail-case-custom-fields {\\\"custom_qa_team\\\":\\\"9\\\"}",
                      "--testrail-case-section-name \'All\'",
                    ]
                    report_result = shared.upload_results_to_testrail(cvp_sanity_report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
                    common.printMsg(report_result, "blue")
                    report_url = report_result.split("\n").each {
                        if (it.contains("[TestRun URL]")) {
                            common.printMsg("Found report URL: " + it.trim().split().last(), "blue")
                            description += "<a href=" + it.trim().split().last() + ">${testSuiteName}</a><br>"
                        }
                    }
                }
            }

        } catch (e) {
            common.printMsg("Job is failed", "purple")
            throw e
        } finally {
            // reporting is failed for some reason
            writeFile(file: "description.txt", text: description, encoding: "UTF-8")
        }
    }
}
