
def jobs_definition = [
    [
        name: "bm-k8s-contrail40-maas",
        lab_config_name: "cookied-cicd-bm-k8s-contrail40-maas",
        drivetrain_stack_install: "core,kvm,cicd",
        drivetrain_stack_install_timeout: "7200",
        platform_stack_install: "k8s,contrail,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8125",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"k8s_conformance|run_stacklight\"",
        shutdown_env_on_teardown: false,
        lab_management_iface: "br-upgrdlab",
        lab_control_iface: "br-k8s-ctl",
        tempest_test_suite_name: "",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "bm-os-contrail40-maas",
        lab_config_name: "cookied-cicd-bm-os-contrail40-maas",
        drivetrain_stack_install: "core,kvm,cicd",
        drivetrain_stack_install_timeout: "7200",
        platform_stack_install: "openstack,contrail,ceph,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8125",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"k8s_conformance|run_stacklight\"",
        shutdown_env_on_teardown: false,
        lab_management_iface: "br-contdpdk",
        lab_control_iface: "br-vsrx-ctl",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "bm-os-contrail40-maas-2018.8.0",
        lab_config_name: "cookied-cicd-bm-os-contrail40-maas-2018.8.0",
        drivetrain_stack_install: "core,kvm,cicd",
        drivetrain_stack_install_timeout: "7200",
        platform_stack_install: "openstack,contrail,ceph,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8125",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"run_tempest|run_stacklight\"",
        shutdown_env_on_teardown: false,
        lab_management_iface: "br-contdpdk",
        lab_control_iface: "br-vsrx-ctl",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "k8s-calico",
        lab_config_name: "cookied-cicd-k8s-calico",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "k8s,calico",
        platform_stack_install_timeout: "3600",
        mcp_version: "proposed",
        node_name: "cz8115",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"k8s_conformance|k8s_calico\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "",

        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "k8s-calico-sl",
        lab_config_name: "cookied-cicd-k8s-calico-sl",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "k8s,calico,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8118",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"k8s_conformance|k8s_calico_sl|k8s_dashboard|k8s_metallb|k8s_ingress_nginx|k8s_virtlet|k8s_conformance_virtlet\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "k8s-calico-sl",
        lab_config_name: "cookied-cicd-k8s-calico-sl",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "k8s,calico,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8118",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"k8s_conformance|k8s_calico_sl|k8s_dashboard|k8s_metallb|k8s_ingress_nginx|k8s_virtlet|k8s_conformance_virtlet\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "k8s-genie",
        lab_config_name: "cookied-cicd-k8s-genie",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "k8s,calico",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8115",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"k8s_conformance|k8s_genie|k8s_calico|k8s_dashboard|k8s_metallb|k8s_ingress_nginx|k8s_conformance_virtlet\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "pike-dpdk",
        lab_config_name: "cookied-cicd-pike-dpdk",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "openstack,ovs",
        platform_stack_install_timeout: "3600",
        mcp_version: "proposed",
        node_name: "cz8121",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"run_tempest\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "pike-dvr-ceph",
        lab_config_name: "cookied-cicd-pike-dvr-ceph",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "6000",
        platform_stack_install: "openstack,ovs,ceph,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8119",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"run_tempest|run_stacklight\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "pike",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "pike-dvr-sl",
        lab_config_name: "cookied-cicd-pike-dvr-sl",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "openstack,ovs,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8122",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"run_tempest|run_stacklight\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "pike-ovs-sl",
        lab_config_name: "cookied-cicd-pike-ovs-sl",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "openstack,ovs,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8116",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"run_tempest|run_stacklight\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ],
    [
        name: "queens-dvr-sl",
        lab_config_name: "cookied-cicd-queens-dvr-sl",
        drivetrain_stack_install: "core,cicd",
        drivetrain_stack_install_timeout: "5400",
        platform_stack_install: "openstack,ovs,stacklight",
        platform_stack_install_timeout: "7200",
        mcp_version: "proposed",
        node_name: "cz8116",
        mcp_image_path1604: "/home/jenkins/images/ubuntu-16-04-x64-mcp\${MCP_VERSION}.qcow2",
        image_path_cfg01_day01: "/home/jenkins/images/cfg01-day01.qcow2",
        cfg01_config_image_name: "cfg01.\${LAB_CONFIG_NAME}-config-drive.iso",
        env_name: "\${LAB_CONFIG_NAME}",
        run_test_opts: "-m \"run_tempest|run_stacklight\"",
        shutdown_env_on_teardown: true,
        lab_management_iface: "",
        lab_control_iface: "",
        tempest_test_suite_name: "[MCP1.1_PIKE]Tempest",
        tempest_image_version: "",
        pipeline: "jobs/pipelines/deploy-cicd-and-run-tests.groovy"
    ]
]

def job_names = []

jobs_definition.each { j ->
    job_names << "cookied-cicd-${j.name}"
    job_names << "runner-cookied-cicd-${j.name}"
    pipelineJob("cookied-cicd-${j.name}") {
        description("Cookicutter model with cicd deployment")
        keepDependencies(false)
        parameters {
            stringParam("LAB_CONFIG_NAME", j.lab_config_name)
            stringParam("DRIVETRAIN_STACK_INSTALL", j.drivetrain_stack_install,
                        "Comma-separated list of stacks to deploy the drivetrain (salt cluster and cicd nodes)")
            stringParam("DRIVETRAIN_STACK_INSTALL_TIMEOUT", j.drivetrain_stack_install_timeout)
            stringParam("PLATFORM_STACK_INSTALL", j.platform_stack_install,
                        "Comma-separated list of stacks to deploy the target platform (k8s and additional components)")
            stringParam("PLATFORM_STACK_INSTALL_TIMEOUT", j.platform_stack_install_timeout)
            stringParam("MCP_VERSION", j.mcp_version)
            stringParam("NODE_NAME", j.node_name)
            stringParam("MCP_IMAGE_PATH1604", j.mcp_image_path1604)
            stringParam("IMAGE_PATH_CFG01_DAY01", j.image_path_cfg01_day01)
            stringParam("CFG01_CONFIG_IMAGE_NAME", j.cfg01_config_image_name,
                        "ISO name that will be generated and downloaded to the /home/jenkins/images/")
            stringParam("ENV_NAME", j.env_name)
            stringParam("TCP_QA_REFS", "",
                        "Example: refs/changes/89/411189/36\n" +
                        "(for now - only one reference allowed)")
            stringParam("PIPELINE_LIBRARY_REF", "", "reference to patchset in pipeline-library")
            stringParam("MK_PIPELINES_REF", "", "reference to patchset in mk-pipelines")
            stringParam("COOKIECUTTER_TEMPLATE_COMMIT", "",
                        "Can be 'master' or 'proposed'. If empty, then takes \${MCP_VERSION} value")
            stringParam("SALT_MODELS_SYSTEM_COMMIT", "",
                        "Can be 'master' or 'proposed'. If empty, then takes \${MCP_VERSION} value")
            stringParam("RUN_TEST_OPTS", j.run_test_opts,
                        "Pytest option -k or -m, with expression to select necessary tests.\n" +
                        "Additional pytest options are allowed.")
            booleanParam("SHUTDOWN_ENV_ON_TEARDOWN", j.shutdown_env_on_teardown, "")
            stringParam("COOKIECUTTER_REF_CHANGE", "", "")
            stringParam("ENVIRONMENT_TEMPLATE_REF_CHANGE", "", "")
            stringParam("TEMPEST_TEST_SUITE_NAME", j.tempest_test_suite_name, "")
            stringParam("TEMPEST_IMAGE_VERSION", j.tempest_image_version, "")
            stringParam("LAB_MANAGEMENT_IFACE", j.lab_management_iface, "")
            stringParam("LAB_CONTROL_IFACE", j.lab_control_iface, "")
        }
        definition {
            cpsScm {
                scm {
                    git {
                        remote {
                            github("https://review.gerrithub.io/Mirantis/tcp-qa", "https")
                        }
                        branch("FETCH_HEAD")
                    }
                }
                scriptPath(j.pipeline)
            }
        }
        disabled(false)
        configure {
            it / 'properties' / 'com.sonyericsson.rebuild.RebuildSettings' {
                'autoRebuild'('false')
                'rebuildDisabled'('false')
            }
        }
    }
    job("runner-cookied-cicd-${j.name}") {
            description "Workaround for https://issues.jenkins-ci.org/browse/JENKINS-38825\n" +
                        "Make possibly to run pipeline-based jobs from multijob."
            label 'cz8133'
            weight 1
            keepDependencies false
            disabled false
            concurrentBuild false
            steps {
                downstreamParameterized {
                    trigger("${j.name}") {
                        block {
                            buildStepFailure("FAILURE")
                            unstable("UNSTABLE")
                            failure("FAILURE")
                        }
                    }
                }
            }
            configure {
                it / 'properties' / 'com.sonyericsson.rebuild.RebuildSettings' {
                    'autoRebuild'('false')
                    'rebuildDisabled'('false')
                }
            }
        }
}

listView("Cookied CICD jobs") {
    description('All CICD Job for intergtation testing')
    jobs {
        job_names.each {
            name it
        }
    }
    columns {
        status()
        weather()
        name()
        lastSuccess()
        lastFailure()
        lastDuration()
        buildButton()
        lastBuildConsole()
    }
}
