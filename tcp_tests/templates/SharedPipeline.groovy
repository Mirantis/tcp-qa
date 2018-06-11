common = new com.mirantis.mk.Common()

def run_cmd(cmd, returnStdout=false) {
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

def generate_cookied_model() {
        // do not fail if environment doesn't exists
        def IPV4_NET_ADMIN=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep admin-pool01").trim().split().last()
        def IPV4_NET_CONTROL=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep private-pool01").trim().split().last()
        def IPV4_NET_TENANT=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep tenant-pool01").trim().split().last()
        def IPV4_NET_EXTERNAL=run_cmd_stdout("dos.py net-list ${ENV_NAME} | grep external-pool01").trim().split().last()
        println("IPV4_NET_ADMIN=" + IPV4_NET_ADMIN)
        println("IPV4_NET_CONTROL=" + IPV4_NET_CONTROL)
        println("IPV4_NET_TENANT=" + IPV4_NET_TENANT)
        println("IPV4_NET_EXTERNAL=" + IPV4_NET_EXTERNAL)

        def parameters = [
                string(name: 'LAB_CONTEXT_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'CLUSTER_NAME', value: "${LAB_CONFIG_NAME}"),
                string(name: 'DOMAIN_NAME', value: "${LAB_CONFIG_NAME}.local"),
                string(name: 'REPOSITORY_SUITE', value: "${MCP_VERSION}"),
                string(name: 'SALT_MODELS_SYSTEM_COMMIT', value: "${MCP_VERSION}"),
                string(name: 'COOKIECUTTER_TEMPLATE_COMMIT', value: "${MCP_VERSION}"),
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

// pretend a groovy class, DO NOT REMOVE
return this