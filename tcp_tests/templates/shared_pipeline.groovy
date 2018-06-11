common = new com.mirantis.mk.Common()

def run_cmd(cmd, returnStdout=false) {
    common.printMsg("Run shell command:\n" + cmd, "blue")
    def VENV_PATH='/home/jenkins/fuel-devops30'
    script = "set +x; echo 'activate python virtualenv ${VENV_PATH}';. ${VENV_PATH}/bin/activate; bash -c 'set -ex;set -ex;${cmd.stripIndent()}'"
    return sh(script: script, returnStdout: returnStdout)
}

def run_cmd_stdout(cmd) {
    //def returnStdout = true
    return run_cmd(cmd, true)
}

def clean_environment_workspace() {
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
}
