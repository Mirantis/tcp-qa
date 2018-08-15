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
            def report_name = ''
            def testSuiteName = ''
            def methodname = ''
            def testrail_name_template = ''
            def reporter_extra_options = []

            stage("Deployment report") {
                report_name = "\$(pwd)/deployment_${ENV_NAME}"
                testSuiteName = "[MCP] Integration automation"
                methodname = '{methodname}'
                testrail_name_template = '{title}'
                reporter_extra_options = [
                  "--testrail-add-missing-cases",
                  "--testrail-case-custom-fields '{\"custom_qa_team\": \"9\"}'",
                  "--testrail-case-section-name 'All'",
                ]
                shared.upload_results_to_testrail(report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options)
            }

            stage("tcp-qa cases report") {
                report_name = "nosetests.xml"
                testSuiteName = "[MCP_X] integration cases"
                methodname = "{methodname}"
                testrail_name_template = "{title}"
                shared.upload_results_to_testrail(report_name, testSuiteName, methodname, testrail_name_template)
            }

            if ('openstack' in stacks) {
                stage("Tempest report") {
                    report_name = "report_*.xml"
                    testSuiteName = "[MCP1.1_PIKE]Tempest"
                    methodname = "{classname}.{methodname}"
                    testrail_name_template = "{title}"
                    shared.upload_results_to_testrail(report_name, testSuiteName, methodname, testrail_name_template)
                }
            }

            if ('k8s' in stacks) {
                stage("Tempest report") {
                    println "TBD"
                    // K8s conformance report
                }
            }

            if ('stacklight' in stacks) {
                stage("stacklight-pytest report") {
                    report_name = "report.xml"
                    testSuiteName = "LMA2.0_Automated"
                    methodname = "{methodname}"
                    testrail_name_template = "{title}"
                    shared.upload_results_to_testrail(report_name, testSuiteName, methodname, testrail_name_template)
                }
            }

        } catch (e) {
            common.printMsg("Job is failed: " + e.message, "red")
            throw e
        } finally {
            // reporting is failed for some reason
        }
    }
}
