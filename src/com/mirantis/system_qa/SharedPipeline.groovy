package com.mirantis.system_qa


def run_cmd(cmd, returnStdout=false) {
    def common = new com.mirantis.mk.Common()
    common.printMsg("Run shell command:\n" + cmd, "blue")
    def VENV_PATH='/home/jenkins/fuel-devops30'
    script = """\
        set +x;
        echo 'activate python virtualenv ${VENV_PATH}';
        . ${VENV_PATH}/bin/activate;
        bash -c 'set -ex; set -ex; ${cmd.stripIndent()}'
    """
    return sh(script: script, returnStdout: returnStdout)
}

def run_cmd_stdout(cmd) {
    return run_cmd(cmd, true)
}


def prepare_working_dir() {
        println "Clean the working directory ${env.WORKSPACE}"
        deleteDir()

        //// do not fail if environment doesn't exists
        // println "Remove environment ${ENV_NAME}"
        // run_cmd("""\
        //     dos.py erase ${ENV_NAME} || true
        // """)
        // println "Remove config drive ISO"
        // run_cmd("""\
        //    rm /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} || true
        // """)

        run_cmd("""\
        git clone https://github.com/Mirantis/tcp-qa.git ${env.WORKSPACE}
        if [ -n "$TCP_QA_REFS" ]; then
            set -e
            git fetch https://review.gerrithub.io/Mirantis/tcp-qa $TCP_QA_REFS && git checkout FETCH_HEAD || exit \$?
        fi
        pip install --upgrade --upgrade-strategy=only-if-needed -r tcp_tests/requirements.txt
        """)
}

def swarm_bootstrap_salt_cluster_devops() {
        def common = new com.mirantis.mk.Common()
        def parameters = [
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'LAB_CONFIG_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'MCP_VERSION', value: "${MCP_VERSION}"),
                string(name: 'MCP_IMAGE_PATH1604', value: "${MCP_IMAGE_PATH1604}"),
                string(name: 'IMAGE_PATH_CFG01_DAY01', value: "${IMAGE_PATH_CFG01_DAY01}"),
                string(name: 'CFG01_CONFIG_IMAGE_NAME', value: "${CFG01_CONFIG_IMAGE_NAME}"),
                string(name: 'TCP_QA_REFS', value: "${TCP_QA_REFS}"),
                string(name: 'PIPELINE_LIBRARY_REF', value: "${PIPELINE_LIBRARY_REF}"),
                string(name: 'MK_PIPELINES_REF', value: "${MK_PIPELINES_REF}"),
                string(name: 'COOKIECUTTER_TEMPLATE_COMMIT', value: "${COOKIECUTTER_TEMPLATE_COMMIT}"),
                string(name: 'SALT_MODELS_SYSTEM_COMMIT', value: "${SALT_MODELS_SYSTEM_COMMIT}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
            ]
        common.printMsg("Start building job 'swarm-bootstrap-salt-cluster-devops' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'swarm-bootstrap-salt-cluster-devops',
            parameters: parameters
}

def swarm_deploy_cicd(String stack_to_install='core,cicd') {
        // Run openstack_deploy job on cfg01 Jenkins for specified stacks
        def common = new com.mirantis.mk.Common()
        def parameters = [
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'STACK_INSTALL', value: stack_to_install),
                string(name: 'TCP_QA_REFS', value: "${TCP_QA_REFS}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
            ]
        common.printMsg("Start building job 'swarm-deploy-cicd' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'swarm-deploy-cicd',
            parameters: parameters
}

def swarm_deploy_platform(String stack_to_install) {
        // Run openstack_deploy job on CICD Jenkins for specified stacks
        def common = new com.mirantis.mk.Common()
        def parameters = [
                string(name: 'PARENT_NODE_NAME', value: "${NODE_NAME}"),
                string(name: 'PARENT_WORKSPACE', value: pwd()),
                string(name: 'ENV_NAME', value: "${ENV_NAME}"),
                string(name: 'STACK_INSTALL', value: stack_to_install),
                string(name: 'TCP_QA_REFS', value: "${TCP_QA_REFS}"),
                booleanParam(name: 'SHUTDOWN_ENV_ON_TEARDOWN', value: false),
            ]
        common.printMsg("Start building job 'swarm-deploy-platform' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'swarm-deploy-platform',
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

        def parameters = [
                string(name: 'LAB_CONTEXT_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'CLUSTER_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'DOMAIN_NAME', value: "${LAB_CONFIG_NAME}.local"),
                string(name: 'REPOSITORY_SUITE', value: "${env.MCP_VERSION}"),
                string(name: 'SALT_MODELS_SYSTEM_COMMIT', value: "${saltmodels_system_commit}"),
                string(name: 'COOKIECUTTER_TEMPLATE_COMMIT', value: "${cookiecuttertemplate_commit}"),
                string(name: 'TCP_QA_REVIEW', value: "${TCP_QA_REFS}"),
                string(name: 'IPV4_NET_ADMIN', value: IPV4_NET_ADMIN),
                string(name: 'IPV4_NET_CONTROL', value: IPV4_NET_CONTROL),
                string(name: 'IPV4_NET_TENANT', value: IPV4_NET_TENANT),
                string(name: 'IPV4_NET_EXTERNAL', value: IPV4_NET_EXTERNAL),
            ]
        common.printMsg("Start building job 'swarm-cookied-model-generator' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'swarm-cookied-model-generator',
            parameters: parameters
}

def generate_configdrive_iso() {
        def common = new com.mirantis.mk.Common()
        def SALT_MASTER_IP=run_cmd_stdout("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            echo \$SALT_MASTER_IP
            """).trim().split().last()
        println("SALT_MASTER_IP=" + SALT_MASTER_IP)
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
                string(name: 'PIPELINE_REPO_URL', value: "https://github.com/Mirantis"),
                booleanParam(name: 'PIPELINES_FROM_ISO', value: true),
                string(name: 'MCP_SALT_REPO_URL', value: "http://apt.mirantis.com/xenial"),
                string(name: 'MCP_SALT_REPO_KEY', value: "http://apt.mirantis.com/public.gpg"),
                string(name: 'PIPELINE_LIBRARY_REF', value: "${PIPELINE_LIBRARY_REF}"),
                string(name: 'MK_PIPELINES_REF', value: "${MK_PIPELINES_REF}"),
            ]
        common.printMsg("Start building job 'create-cfg-config-drive' with parameters:", "purple")
        common.prettyPrint(parameters)
        build job: 'create-cfg-config-drive',
            parameters: parameters
}

def run_job_on_day01_node(stack_to_install, timeout=1800) {
    // stack_to_install="core,cicd"
    def stack = "${stack_to_install}"
    run_cmd("""\
        export ENV_NAME=${ENV_NAME}
        . ./tcp_tests/utils/env_salt
        . ./tcp_tests/utils/env_jenkins_day01
        export JENKINS_BUILD_TIMEOUT=${timeout}
        JOB_PARAMETERS=\"{
            \\\"SALT_MASTER_URL\\\": \\\"\${SALTAPI_URL}\\\",
            \\\"STACK_INSTALL\\\": \\\"${stack}\\\"
        }\"
        JOB_PREFIX="[ {job_name}/{build_number}:${stack} {time} ] "
        python ./tcp_tests/utils/run_jenkins_job.py --verbose --job-name=deploy_openstack --job-parameters="\$JOB_PARAMETERS" --job-output-prefix="\$JOB_PREFIX"
    """)
}

def run_job_on_cicd_nodes(stack_to_install, timeout=1800) {
    // stack_to_install="k8s,calico,stacklight"
    def stack = "${stack_to_install}"
    run_cmd("""\
        export ENV_NAME=${ENV_NAME}
        . ./tcp_tests/utils/env_salt
        . ./tcp_tests/utils/env_jenkins_cicd
        export JENKINS_BUILD_TIMEOUT=${timeout}
        JOB_PARAMETERS=\"{
            \\\"SALT_MASTER_URL\\\": \\\"\${SALTAPI_URL}\\\",
            \\\"STACK_INSTALL\\\": \\\"${stack}\\\"
        }\"
        JOB_PREFIX="[ {job_name}/{build_number}:${stack} {time} ] "
        python ./tcp_tests/utils/run_jenkins_job.py --verbose --job-name=deploy_openstack --job-parameters="\$JOB_PARAMETERS" --job-output-prefix="\$JOB_PREFIX"
        sleep 60  # Wait for IO calm down on cluster nodes
    """)
}

def sanity_check_component(stack) {
    // Run sanity check for the component ${stack}.
    // Result will be stored in JUnit XML file deploy_${stack}.xml
    run_cmd("""\
        py.test --junit-xml=deploy_${stack}.xml -m check_${stack}
    """)
}

def devops_snapshot(stack) {
    // Make the snapshot with name "${stack}_deployed"
    // for all VMs in the environment.
    // If oslo_config INI file ${ENV_NAME}_salt_deployed.ini exists,
    // then make a copy for the created snapshot to allow the system
    // tests to revert this snapshot along with the metadata from the INI file.
    run_cmd("""\
        dos.py suspend ${ENV_NAME}
        dos.py snapshot ${ENV_NAME} ${stack}_deployed
        dos.py resume ${ENV_NAME}
        dos.py time-sync ${ENV_NAME}
        if [ -f \$(pwd)/${ENV_NAME}_salt_deployed.ini ]; then
            cp \$(pwd)/${ENV_NAME}_salt_deployed.ini \$(pwd)/${ENV_NAME}_${stack}_deployed.ini
        fi
    """)
}

def report_deploy_result(deploy_expected_stacks) {
}

def report_test_result() {
}