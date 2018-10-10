package com.mirantis.system_qa

import groovy.xml.XmlUtil

def run_sh(String cmd) {
    // run shell script without catching any output
    def common = new com.mirantis.mk.Common()
    common.printMsg("Run shell command:\n" + cmd, "blue")
    def VENV_PATH='/home/jenkins/fuel-devops30'
    script = """\
        set -ex;
        . ${VENV_PATH}/bin/activate;
        bash -c '${cmd.stripIndent()}'
    """
    return sh(script: script)
}

def run_cmd(String cmd, Boolean returnStdout=false) {
    def common = new com.mirantis.mk.Common()
    common.printMsg("Run shell command:\n" + cmd, "blue")
    def VENV_PATH='/home/jenkins/fuel-devops30'
    def stderr_path = "/tmp/${JOB_NAME}_${BUILD_NUMBER}_stderr.log"
    script = """\
        set +x;
        echo 'activate python virtualenv ${VENV_PATH}';
        . ${VENV_PATH}/bin/activate;
        bash -c 'set -ex; set -ex; ${cmd.stripIndent()}' 2>${stderr_path}
    """
    def result
    try {
        return sh(script: script, returnStdout: returnStdout)
    } catch (e) {
        def stderr = readFile("${stderr_path}")
        def error_message = e.message + "\n<<<<<< STDERR: >>>>>>\n" + stderr
        throw new Exception(error_message)
    } finally {
        sh(script: "rm ${stderr_path} || true")
    }
}

def run_cmd_stdout(cmd) {
    return run_cmd(cmd, true)
}

def build_pipeline_job(job_name, parameters) {
    //Build a job, grab the results if failed and use the results in exception
    def common = new com.mirantis.mk.Common()
    common.printMsg("Start building job '${job_name}' with parameters:", "purple")
    common.prettyPrint(parameters)

    def job_info = build job: "${job_name}",
        parameters: parameters,
        propagate: false

    if (job_info.getResult() != "SUCCESS") {
        currentBuild.result = job_info.getResult()
        def build_number = job_info.getNumber()
        common.printMsg("Job '${job_name}' failed, getting details", "red")
        def workflow_details=run_cmd_stdout("""\
            export JOB_NAME=${job_name}
            export BUILD_NUMBER=${build_number}
            python ./tcp_tests/utils/get_jenkins_job_stages.py
            """)
        throw new Exception(workflow_details)
    }
}

def build_shell_job(job_name, parameters, junit_report_filename=null, junit_report_source_dir='**/') {
    //Build a job, grab the results if failed and use the results in exception
    //junit_report_filename: if not null, try to copy this JUnit report first from remote job
    def common = new com.mirantis.mk.Common()
    common.printMsg("Start building job '${job_name}' with parameters:", "purple")
    common.prettyPrint(parameters)

    def job_info = build job: "${job_name}",
        parameters: parameters,
        propagate: false

    if (job_info.getResult() != "SUCCESS") {
        def build_status = job_info.getResult()
        def build_number = job_info.getNumber()
        def build_url = job_info.getAbsoluteUrl()
        def job_url = "${build_url}"
        currentBuild.result = build_status
        if (junit_report_filename) {
            common.printMsg("Job '${job_url}' failed with status ${build_status}, getting details", "red")
            step($class: 'hudson.plugins.copyartifact.CopyArtifact',
                 projectName: job_name,
                 selector: specific("${build_number}"),
                 filter: "${junit_report_source_dir}/${junit_report_filename}",
                 target: '.',
                 flatten: true,
                 fingerprintArtifacts: true)

            def String junit_report_xml = readFile("${junit_report_filename}")
            def String junit_report_xml_pretty = new XmlUtil().serialize(junit_report_xml)
            // Replace '<' and '>' to '&lt;' and '&gt;' to avoid conflicts between xml tags in the message and JUnit report
            def String junit_report_xml_filtered = junit_report_xml_pretty.replaceAll("<","&lt;").replaceAll(">", "&gt;")
            def String msg = "Job '${job_url}' failed with status ${build_status}, JUnit report:\n"
            throw new Exception(msg + junit_report_xml_filtered)
        } else {
            throw new Exception("Job '${job_url}' failed with status ${build_status}, please check the console output.")
        }
    }
}

def prepare_working_dir() {
        println "Clean the working directory ${env.WORKSPACE}"
        deleteDir()

        // do not fail if environment doesn't exists
        println "Remove environment ${ENV_NAME}"
        run_cmd("""\
            dos.py erase ${ENV_NAME} || true
        """)
        println "Remove config drive ISO"
        run_cmd("""\
            rm /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} || true
        """)

        run_cmd("""\
            git clone https://github.com/Mirantis/tcp-qa.git ${env.WORKSPACE}
            if [ -n "$TCP_QA_REFS" ]; then
                set -e
                git fetch https://review.gerrithub.io/Mirantis/tcp-qa $TCP_QA_REFS && git checkout FETCH_HEAD || exit \$?
            fi
            pip install --upgrade --upgrade-strategy=only-if-needed -r tcp_tests/requirements.txt
        """)
}

def update_working_dir() {
        // Use to fetch a patchset from gerrit to the working dir
        run_cmd("""\
            if [ -n "$TCP_QA_REFS" ]; then
                set -e
                git fetch https://review.gerrithub.io/Mirantis/tcp-qa $TCP_QA_REFS && git checkout FETCH_HEAD || exit \$?
            fi
            pip install -r tcp_tests/requirements.txt
        """)
}

def swarm_bootstrap_salt_cluster_devops() {
        def common = new com.mirantis.mk.Common()
        def cookiecutter_template_commit = env.COOKIECUTTER_TEMPLATE_COMMIT ?: env.MCP_VERSION
        def salt_models_system_commit = env.SALT_MODELS_SYSTEM_COMMIT ?: env.MCP_VERSION
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''
        def mk_pipelines_ref = env.MK_PIPELINES_REF ?: ''
        def pipeline_library_ref = env.PIPELINE_LIBRARY_REF ?: ''
        def cookiecutter_ref_change = env.COOKIECUTTER_REF_CHANGE ?: ''
        def environment_template_ref_change = env.ENVIRONMENT_TEMPLATE_REF_CHANGE ?: ''
        def parameters = [
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'LAB_CONFIG_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'MCP_VERSION', value: "${MCP_VERSION}"),
                string(name: 'MCP_IMAGE_PATH1604', value: "${MCP_IMAGE_PATH1604}"),
                string(name: 'IMAGE_PATH_CFG01_DAY01', value: "${IMAGE_PATH_CFG01_DAY01}"),
                string(name: 'CFG01_CONFIG_IMAGE_NAME', value: "${CFG01_CONFIG_IMAGE_NAME}"),
                string(name: 'TCP_QA_REFS', value: "${tcp_qa_refs}"),
                string(name: 'PIPELINE_LIBRARY_REF', value: "${pipeline_library_ref}"),
                string(name: 'MK_PIPELINES_REF', value: "${mk_pipelines_ref}"),
                string(name: 'COOKIECUTTER_TEMPLATE_COMMIT', value: "${cookiecutter_template_commit}"),
                string(name: 'SALT_MODELS_SYSTEM_COMMIT', value: "${salt_models_system_commit}"),
                string(name: 'COOKIECUTTER_REF_CHANGE', value: "${cookiecutter_ref_change}"),
                string(name: 'ENVIRONMENT_TEMPLATE_REF_CHANGE', value: "${environment_template_ref_change}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
            ]

        build_pipeline_job('swarm-bootstrap-salt-cluster-devops', parameters)
}

def swarm_deploy_cicd(String stack_to_install='core,cicd') {
        // Run openstack_deploy job on cfg01 Jenkins for specified stacks
        def common = new com.mirantis.mk.Common()
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''
        def parameters = [
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'STACK_INSTALL', value: stack_to_install),
                string(name: 'TCP_QA_REFS', value: "${tcp_qa_refs}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
            ]
        build_pipeline_job('swarm-deploy-cicd', parameters)
}

def swarm_deploy_platform(String stack_to_install) {
        // Run openstack_deploy job on CICD Jenkins for specified stacks
        def common = new com.mirantis.mk.Common()
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''
        def parameters = [
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'STACK_INSTALL', value: stack_to_install),
                string(name: 'TCP_QA_REFS', value: "${tcp_qa_refs}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
            ]
        build_pipeline_job('swarm-deploy-platform', parameters)
}

def swarm_run_pytest(String passed_steps) {
        // Run pytest tests
        def common = new com.mirantis.mk.Common()
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''
        def parameters = [
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'PASSED_STEPS', value: passed_steps),
                string(name: 'RUN_TEST_OPTS', value: "${RUN_TEST_OPTS}"),
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'TCP_QA_REFS', value: "${tcp_qa_refs}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
                string(name: 'LAB_CONFIG_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'REPOSITORY_SUITE', value: "${MCP_VERSION}"),
                string(name: 'MCP_IMAGE_PATH1604', value: "${MCP_IMAGE_PATH1604}"),
                string(name: 'IMAGE_PATH_CFG01_DAY01', value: "${IMAGE_PATH_CFG01_DAY01}"),
            ]
        common.printMsg("Start building job 'swarm-run-pytest' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'swarm-run-pytest',
            parameters: parameters
}

def swarm_testrail_report(String passed_steps) {
        // Run pytest tests
        def common = new com.mirantis.mk.Common()
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''
        def parameters = [
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'MCP_VERSION', value: "${MCP_VERSION}"),
                string(name: 'PASSED_STEPS', value: passed_steps),
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'TCP_QA_REFS', value: "${tcp_qa_refs}"),
            ]
        common.printMsg("Start building job 'swarm-testrail-report' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'swarm-testrail-report',
            parameters: parameters
}

def generate_cookied_model() {
        def common = new com.mirantis.mk.Common()
        // do not fail if environment doesn't exists
        def IPV4_NET_ADMIN=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep admin-pool01").trim().split().last()
        def IPV4_NET_CONTROL=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep private-pool01").trim().split().last()
        def IPV4_NET_TENANT=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep tenant-pool01").trim().split().last()
        def IPV4_NET_EXTERNAL=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep external-pool01").trim().split().last()
        println("IPV4_NET_ADMIN=" + IPV4_NET_ADMIN)
        println("IPV4_NET_CONTROL=" + IPV4_NET_CONTROL)
        println("IPV4_NET_TENANT=" + IPV4_NET_TENANT)
        println("IPV4_NET_EXTERNAL=" + IPV4_NET_EXTERNAL)

        def cookiecuttertemplate_commit = env.COOKIECUTTER_TEMPLATE_COMMIT ?: env.MCP_VERSION
        def saltmodels_system_commit = env.SALT_MODELS_SYSTEM_COMMIT ?: env.MCP_VERSION
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''
        def environment_template_ref_change = env.ENVIRONMENT_TEMPLATE_REF_CHANGE ?: ''
        def cookiecutter_ref_change = env.COOKIECUTTER_REF_CHANGE ?: ''

        def parameters = [
                string(name: 'LAB_CONTEXT_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'CLUSTER_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'DOMAIN_NAME', value: "${LAB_CONFIG_NAME}.local"),
                string(name: 'REPOSITORY_SUITE', value: "${env.MCP_VERSION}"),
                string(name: 'SALT_MODELS_SYSTEM_COMMIT', value: "${saltmodels_system_commit}"),
                string(name: 'COOKIECUTTER_TEMPLATE_COMMIT', value: "${cookiecuttertemplate_commit}"),
                string(name: 'COOKIECUTTER_REF_CHANGE', value: "${cookiecutter_ref_change}"),
                string(name: 'ENVIRONMENT_TEMPLATE_REF_CHANGE', value: "${environment_template_ref_change}"),
                string(name: 'TCP_QA_REVIEW', value: "${tcp_qa_refs}"),
                string(name: 'IPV4_NET_ADMIN', value: IPV4_NET_ADMIN),
                string(name: 'IPV4_NET_CONTROL', value: IPV4_NET_CONTROL),
                string(name: 'IPV4_NET_TENANT', value: IPV4_NET_TENANT),
                string(name: 'IPV4_NET_EXTERNAL', value: IPV4_NET_EXTERNAL),
            ]

        build_shell_job('swarm-cookied-model-generator', parameters, "deploy_generate_model.xml")
}

def generate_configdrive_iso() {
        def common = new com.mirantis.mk.Common()
        def SALT_MASTER_IP=run_cmd_stdout("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            echo \$SALT_MASTER_IP
            """).trim().split().last()
        println("SALT_MASTER_IP=" + SALT_MASTER_IP)

        def dhcp_ranges_json=run_cmd_stdout("""\
            fgrep dhcp_ranges ${ENV_NAME}_hardware.ini |
            fgrep "admin-pool01"|
            awk -F"=" '{print $2}'
            """).trim()
        def dhcp_ranges = new JsonSlurper().parseText(dhcp_ranges_json)
        def ADMIN_NETWORK_GW = dhcp_ranges['admin-pool01']['gateway']
        println("ADMIN_NETWORK_GW=" + ADMIN_NETWORK_GW)

        def mk_pipelines_ref = env.MK_PIPELINES_REF ?: ''
        def pipeline_library_ref = env.PIPELINE_LIBRARY_REF ?: ''
        def tcp_qa_refs = env.TCP_QA_REFS ?: ''

        def parameters = [
                string(name: 'CLUSTER_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'MODEL_URL', value: "http://cz8133.bud.mirantis.net:8098/${LAB_CONFIG_NAME}.git"),
                string(name: 'MODEL_URL_OBJECT_TYPE', value: "git"),
                booleanParam(name: 'DOWNLOAD_CONFIG_DRIVE', value: true),
                string(name: 'MCP_VERSION', value: "${MCP_VERSION}"),
                string(name: 'COMMON_SCRIPTS_COMMIT', value: "${MCP_VERSION}"),
                string(name: 'NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'CONFIG_DRIVE_ISO_NAME', value: "${CFG01_CONFIG_IMAGE_NAME}"),
                string(name: 'SALT_MASTER_DEPLOY_IP', value: SALT_MASTER_IP),
                string(name: 'DEPLOY_NETWORK_GW', value: ADMIN_NETWORK_GW),
                string(name: 'PIPELINE_REPO_URL', value: "https://github.com/Mirantis"),
                booleanParam(name: 'PIPELINES_FROM_ISO', value: true),
                string(name: 'MCP_SALT_REPO_URL', value: "http://apt.mirantis.com/xenial"),
                string(name: 'MCP_SALT_REPO_KEY', value: "http://apt.mirantis.com/public.gpg"),
                string(name: 'PIPELINE_LIBRARY_REF', value: "${pipeline_library_ref}"),
                string(name: 'MK_PIPELINES_REF', value: "${mk_pipelines_ref}"),
                string(name: 'TCP_QA_REFS', value: "${tcp_qa_refs}"),
            ]
        build_pipeline_job('swarm-create-cfg-config-drive', parameters)
}

def run_job_on_day01_node(stack_to_install, timeout=2400) {
    // stack_to_install="core,cicd"
    def stack = "${stack_to_install}"
    try {
        run_cmd("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_jenkins_day01
            export JENKINS_BUILD_TIMEOUT=${timeout}
            JOB_PARAMETERS=\"{
                \\\"SALT_MASTER_URL\\\": \\\"\${SALTAPI_URL}\\\",
                \\\"STACK_INSTALL\\\": \\\"${stack}\\\"
            }\"
            JOB_PREFIX="[ ${ENV_NAME}/{build_number}:${stack} {time} ] "
            python ./tcp_tests/utils/run_jenkins_job.py --verbose --job-name=deploy_openstack --job-parameters="\$JOB_PARAMETERS" --job-output-prefix="\$JOB_PREFIX"
        """)
    } catch (e) {
        def common = new com.mirantis.mk.Common()
        common.printMsg("Product job 'deploy_openstack' failed, getting details", "red")
        def workflow_details=run_cmd_stdout("""\
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_jenkins_day01
            export JOB_NAME=deploy_openstack
            export BUILD_NUMBER=lastBuild
            python ./tcp_tests/utils/get_jenkins_job_stages.py
            """)
        throw new Exception(workflow_details)
    }
}

def run_job_on_cicd_nodes(stack_to_install, timeout=2400) {
    // stack_to_install="k8s,calico,stacklight"
    def stack = "${stack_to_install}"
    try {
        run_cmd("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_jenkins_cicd
            export JENKINS_BUILD_TIMEOUT=${timeout}
            JOB_PARAMETERS=\"{
                \\\"SALT_MASTER_URL\\\": \\\"\${SALTAPI_URL}\\\",
                \\\"STACK_INSTALL\\\": \\\"${stack}\\\"
            }\"
            JOB_PREFIX="[ ${ENV_NAME}/{build_number}:${stack} {time} ] "
            python ./tcp_tests/utils/run_jenkins_job.py --verbose --job-name=deploy_openstack --job-parameters="\$JOB_PARAMETERS" --job-output-prefix="\$JOB_PREFIX"
            sleep 60  # Wait for IO calm down on cluster nodes
        """)
    } catch (e) {
        def common = new com.mirantis.mk.Common()
        common.printMsg("Product job 'deploy_openstack' failed, getting details", "red")
        def workflow_details=run_cmd_stdout("""\
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_jenkins_cicd
            export JOB_NAME=deploy_openstack
            export BUILD_NUMBER=lastBuild
            python ./tcp_tests/utils/get_jenkins_job_stages.py
            """)
        throw new Exception(workflow_details)
    }
}

def sanity_check_component(stack) {
    // Run sanity check for the component ${stack}.
    // Result will be stored in JUnit XML file deploy_${stack}.xml
    try {
        run_cmd("""\
            py.test --junit-xml=deploy_${stack}.xml -m check_${stack}
        """)
    } catch (e) {
        def String junit_report_xml = readFile("deploy_${stack}.xml")
        def String junit_report_xml_pretty = new XmlUtil().serialize(junit_report_xml)
        def String msg = "Sanity check for '${stack}' failed, JUnit report:\n"
        throw new Exception(msg + junit_report_xml_pretty)
    }
}

def devops_snapshot(stack) {
    // Make the snapshot with name "${stack}_deployed"
    // for all VMs in the environment.
    // If oslo_config INI file ${ENV_NAME}_salt_deployed.ini exists,
    // then make a copy for the created snapshot to allow the system
    // tests to revert this snapshot along with the metadata from the INI file.
    run_cmd("""\
        set -ex
        dos.py suspend ${ENV_NAME}
        dos.py snapshot ${ENV_NAME} ${stack}_deployed
        dos.py resume ${ENV_NAME}
        sleep 20    # Wait for I/O on the host calms down

        CFG01_NAME=\$(dos.py show-resources ${ENV_NAME} | grep ^cfg01 | cut -d" " -f1)
        dos.py time-sync ${ENV_NAME} --skip-sync \${CFG01_NAME}

        if [ -f \$(pwd)/${ENV_NAME}_salt_deployed.ini ]; then
            cp \$(pwd)/${ENV_NAME}_salt_deployed.ini \$(pwd)/${ENV_NAME}_${stack}_deployed.ini
        fi
    """)
}

def get_steps_list(steps) {
    // Make a list from comma separated string
    return steps.split(',').collect { it.split(':')[0] }
}

def create_xml_report(String filename, String classname, String name, String status='success', String status_message='', String text='', String stdout='', String stderr='') {
    // <filename> is name of the XML report file that will be created
    // <status> is one of the 'success', 'skipped', 'failure' or 'error'
    // 'error' status is assumed as 'Blocker' in TestRail reporter
    def script = """\
<?xml version=\"1.0\" encoding=\"utf-8\"?>
  <testsuite>
    <testcase classname=\"${classname}\" name=\"${name}\" time=\"0\">
      <${status} message=\"${status_message}\">${text}</${status}>
      <system-out>${stdout}</system-out>
      <system-err>${stderr}</system-err>
    </testcase>
  </testsuite>
"""
    writeFile(file: filename, text: script, encoding: "UTF-8")
}

def upload_results_to_testrail(report_name, testSuiteName, methodname, testrail_name_template, reporter_extra_options=[]) {
  def venvPath = '/home/jenkins/venv_testrail_reporter'
  def testPlanDesc = env.ENV_NAME
  def testrailURL = "https://mirantis.testrail.com"
  def testrailProject = "Mirantis Cloud Platform"
  def testPlanName = "[MCP-Q2]System-${MCP_VERSION}-${new Date().format('yyyy-MM-dd')}"
  def testrailMilestone = "MCP1.1"
  def jobURL = env.BUILD_URL

  def reporterOptions = [
    "--verbose",
    "--env-description \"${testPlanDesc}\"",
    "--testrail-run-update",
    "--testrail-url \"${testrailURL}\"",
    "--testrail-user \"\${TESTRAIL_USER}\"",
    "--testrail-password \"\${TESTRAIL_PASSWORD}\"",
    "--testrail-project \"${testrailProject}\"",
    "--testrail-plan-name \"${testPlanName}\"",
    "--testrail-milestone \"${testrailMilestone}\"",
    "--testrail-suite \"${testSuiteName}\"",
    "--xunit-name-template \"${methodname}\"",
    "--testrail-name-template \"${testrail_name_template}\"",
    "--test-results-link \"${jobURL}\"",
  ] + reporter_extra_options

  def script = """
    . ${venvPath}/bin/activate
    set -ex
    report ${reporterOptions.join(' ')} ${report_name}
  """

  def testrail_cred_id = params.TESTRAIL_CRED ?: 'testrail_system_tests'

  withCredentials([
             [$class          : 'UsernamePasswordMultiBinding',
             credentialsId   : testrail_cred_id,
             passwordVariable: 'TESTRAIL_PASSWORD',
             usernameVariable: 'TESTRAIL_USER']
  ]) {
    return run_cmd(script)
  }
}


def create_deploy_result_report(deploy_expected_stacks, result, text) {
    def STATUS_MAP = ['SUCCESS': 'success', 'FAILURE': 'failure', 'UNSTABLE': 'failure', 'ABORTED': 'error']
    def classname = "Deploy"
    def name = "deployment_${ENV_NAME}"
    def filename = "${name}.xml"
    def status = STATUS_MAP[result ?: 'FAILURE']   // currentBuild.result *must* be set at the finish of the try/catch
    create_xml_report(filename, classname, name, status, "Deploy components: ${deploy_expected_stacks}", text, '', '')
}
