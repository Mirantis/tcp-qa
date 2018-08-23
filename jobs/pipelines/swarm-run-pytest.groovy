/**
 *
 * Deploy the product cluster using Jenkins master on CICD cluster
 *
 * Expected parameters:

 *   ENV_NAME                      Fuel-devops environment name
 *   PASSED_STEPS                  Steps passed to install components using Jenkins on CICD cluster: "salt,core,cicd,openstack:3200,stacklight:2400",
                                   where 3200 and 2400 might be timeouts (not used in the testing pipeline)
 *   RUN_TEST_OPTS                 Pytest option -k or -m, with expression to select necessary tests. Additional pytest options are allowed.
 *   PARENT_NODE_NAME              Name of the jenkins slave to create the environment
 *   PARENT_WORKSPACE              Path to the workspace of the parent job to use tcp-qa repo
 *   TCP_QA_REFS                   Reference to the tcp-qa change on review.gerrithub.io, like refs/changes/46/418546/41
 *   SHUTDOWN_ENV_ON_TEARDOWN      optional, shutdown fuel-devops environment at the end of the job
 *   LAB_CONFIG_NAME               Not used (backward compatibility, for manual deployment steps only)
 *   REPOSITORY_SUITE              Not used (backward compatibility, for manual deployment steps only)
 *   MCP_IMAGE_PATH1604            Not used (backward compatibility, for manual deployment steps only)
 *   IMAGE_PATH_CFG01_DAY01        Not used (backward compatibility, for manual deployment steps only)
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

            stage("Run tests") {
                def steps = shared.get_steps_list(PASSED_STEPS)
                def sources = """\
                    export ENV_NAME=${ENV_NAME}
                    . ./tcp_tests/utils/env_salt"""
                if (steps.contains('k8s')) {
                    sources += """
                    . ./tcp_tests/utils/env_k8s\n"""
                }
                if (steps.contains('openstack')) {
                    sources += """
                    # TODO: . ./tcp_tests/utils/env_keystonercv3\n"""
                }
                def installed = steps.collect {"""\
                    export ${it}_installed=true"""}.join("\n")

                shared.run_cmd(sources + installed + """
                    export MANAGER=devops  # use 'hardware' fixture to manage fuel-devops environment
                    export salt_master_host=\$SALT_MASTER_IP  # skip salt_deployed fixture
                    export salt_master_port=6969
                    export SALT_USER=\$SALTAPI_USER
                    export SALT_PASSWORD=\$SALTAPI_PASS

                    py.test --junit-xml=nosetests.xml ${RUN_TEST_OPTS}

                    dos.py suspend ${ENV_NAME}
                    dos.py snapshot ${ENV_NAME} test_completed
                    """)
            }

        } catch (e) {
            common.printMsg("Job is failed" + e.message, "red")
            throw e
        } finally {
            // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
            // and report appropriate data to TestRail
            if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "true") {
                shared.run_cmd("""\
                    dos.py destroy ${ENV_NAME}
                """)
            }
        }
    }
}
