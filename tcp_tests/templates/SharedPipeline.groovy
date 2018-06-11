package tcp_tests.templates

common = new com.mirantis.mk.Common()

def print_some() {
}

def run_cmd(cmd, returnStdout=false) {
    common.printMsg("Run shell command:\n" + cmd, "blue")
    def VENV_PATH='/home/jenkins/fuel-devops30'
    script = "set +x; echo 'activate python virtualenv ${VENV_PATH}';. ${VENV_PATH}/bin/activate; bash -c 'set -ex;set -ex;${cmd.stripIndent()}'"
    return sh(script: script, returnStdout: returnStdout)
}

def run_cmd_stdout(cmd) {
    return run_cmd(cmd, true)
}

def print_some() {
    common.printMsg("TESSSSSSSSSSSSSTTTTTTTTTTTTTTT\n" + cmd, "red")
}
