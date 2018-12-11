
def nodes = [
    'cz8114', 'cz8115', 'cz8116', 'cz8117', 'cz8118', 'cz8119',
    'cz8120', 'cz8121', 'cz8121', 'cz8122', 'cz8123', 'cz8124',
    'cz8124', 'cz8125', 'cz8126', 'cz8127', 'cz8128', 'cz8129',
    'cz8130', 'cz8131', 'cz8132', 'cz8133'
]

def jobs = [
    [ name: "pike-ovs-l2gw-bgpvpn",
      node: "cz8126",
      cluster: "virtual-mcp-pike-ovs",
      domain: "pike-ovs-l2gw-bgpvpn",
      tempest_pattern: "",
      test_group: "test_mcp_pike_ovs_l2gw_bgpvpn_install",
      env_name: "swarm-pike-ovs-l2gw-bgpvpn"
      lab: "virtual-mcp-pike-ovs-l2gw-bgpvpn" ],
    [ name: "Pike-dvr-Policy",
      node: "cz8119",
      cluster: "",
      domain: "",
      tempest_pattern: "",
      test_group: "",
      lab: "" ],
    [ name: "backup-cinder",
      node: "cz8119",
      cluster: "",
      domain: "",
      tempest_pattern: "",
      test_group: "",
      lab: "" ]
]

for (j in  jobs) {
    job("virtual-mcp-${j.name}") {
        logRotator {
            daysToKeep(30)
            artifactNumToKeep(30)
        }
        parameters {
            nodeParam('NODE') {
                description('Chose the node')
                defaultNodes(["${j.node}"])
                allowedNodes(nodes)
                trigger('multiSelectionDisallowed')
                eligibility('IgnoreOfflineNodeEligibility')
            }
            choiceParam('REPOSITORY_SUITE',  ['proposed', 'testing', 'stable', 'nightly'])
            booleanParam('RUN_TEMPEST', true)
            booleanParam('SHUTDOWN_ENV_ON_TEARDOWN', true)
            stringParam('LAB_CONFIG_NAME', "${j.lab}")
            stringParam('TCP_QA_REVIEW', '')
            stringParam('CLUSTER_NAME', "${j.cluster}")
            stringParam('PATTERN', "")
            stringParam('TEMPEST_PATTERN', "")
            stringParam('ROLES', '["salt_master", "salt_minion", "k8s_controller", "vm"]')
            stringParam('MCP_IMAGE_PATH1604', "/home/jenkins/images/ubuntu-16-04-x64-mcpproposed.qcow2")
            stringParam('PATTERN', "")
            stringParam('TEST_GROUP', "${j.test_group}")
            stringParam('TR_CREADS', "testrail-tleontovhich")
        }
        weight(16)
        throttleConcurrentBuilds {
            maxPerNode(1)
            maxTotal(1)
        }
        scm {
            git("https://github.com/Mirantis/tcp-qa.git")
        }
        wrappers {
            timeout {
                absolute(720)
                writeDescription("Timeout")
            }
            colorizeOutput('xterm')
            environmentVariables {
                env('VENV_PATH', '/home/jenkins/fuel-devops30')
                env('REPORT_VENV_PATH', '/home/jenkins/venv_testrail_reporter')
                env('IMAGE_PATH_CFG01_DAY01', '/home/jenkins/images/cfg01-day01.qcow2')
                env('PYTHONIOENCODING', 'UTF-8')
                env('IMAGE_PATH1604', "\$MCP_IMAGE_PATH1604")
                env('ENV_NAME', "${j.env_name}")
            }
            credentialsBinding {
                usernamePassword("TR_USERNAME", "TR_PASSWORD", "\$TR_CREADS")
            }
        }
        steps {
            shell(readFileFromWorkspace('jobs/scripts/run_tcp_qa.sh'))
        }
        publishers {
            archiveArtifacts {
                pattern('tcp_tests/*.ini')
                pattern('tcp_tests/*.log')
                pattern('**/nosetests.xml')
                pattern('**/report*.xml')
                pattern('**/*.tar.gz')
            }
            postBuildScripts {
                steps{
                    shell(". ${VENV_PATH}/bin/activate; dos.py destroy \$ENV_NAME")
                    shell(readFileFromWorkspace('jobs/scripts/run_tr_report.sh'))
                }
            }
            archiveJunit('**/nosetests.xml,**/*.xml') {
                healthScaleFactor(1)
            }
        }
    }
}