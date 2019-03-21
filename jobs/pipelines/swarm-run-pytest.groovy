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
 *   TEMPEST_IMAGE_VERSION         Tempest image version: pike by default, can be queens.
 *   TEMPEST_TARGET                Node where tempest will be run
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

            if (env.TCP_QA_REFS) {
                stage("Update working dir to patch ${TCP_QA_REFS}") {
                    shared.update_working_dir()
                }
            }

            stage("Run tests") {
                def steps = shared.get_steps_list(PASSED_STEPS)
                def sources = """\
                    cd ${PARENT_WORKSPACE}
                    export ENV_NAME=${ENV_NAME}
                    . ./tcp_tests/utils/env_salt"""
                if (steps.contains('k8s')) {
                    sources += """
                    . ./tcp_tests/utils/env_k8s\n"""
                }
                if (steps.contains('openstack')) {
                    sources += """
                    export TEMPEST_IMAGE_VERSION=${TEMPEST_IMAGE_VERSION}
                    export TEMPEST_TARGET=${TEMPEST_TARGET}
                    # TODO: . ./tcp_tests/utils/env_keystonercv3\n"""
                }
                def installed = steps.collect {"""\
                    export ${it}_installed=true"""}.join("\n")

                shared.run_sh(sources + installed + """
                    export TESTS_CONFIGS=${ENV_NAME}_salt_deployed.ini
                    export ENV_MANAGER=devops  # use 'hardware' fixture to manage fuel-devops environment
                    export salt_master_host=\$SALT_MASTER_IP  # skip salt_deployed fixture
                    export salt_master_port=6969
                    export SALT_USER=\$SALTAPI_USER
                    export SALT_PASSWORD=\$SALTAPI_PASS

                    py.test --junit-xml=nosetests.xml ${RUN_TEST_OPTS}

                    """)

                def snapshot_name = "test_completed"
                shared.download_logs("test_completed_${ENV_NAME}")
                shared.run_cmd("""\
                    dos.py suspend ${ENV_NAME}
                    dos.py snapshot ${ENV_NAME} ${snapshot_name}
                """)
                if ("${env.SHUTDOWN_ENV_ON_TEARDOWN}" == "false") {
                    shared.run_cmd("""\
                        dos.py resume ${ENV_NAME}
                    """)
                }
                shared.devops_snapshot_info(snapshot_name)
            }

        } catch (e) {
            common.printMsg("Job is failed", "purple")
            // Downloading logs usually not needed here
            // because tests should use the decorator @pytest.mark.grab_versions
            // shared.download_logs("test_failed_${ENV_NAME}")
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
