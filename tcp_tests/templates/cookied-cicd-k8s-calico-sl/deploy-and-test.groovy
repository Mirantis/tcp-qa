common = new com.mirantis.mk.Common()

def run_cmd(cmd, returnStdout=false) {
    common.printMsg("Run shell command:\n" + cmd, "blue")
    def VENV_PATH='/home/jenkins/fuel-devops30'
    script = "set +x; echo 'activate python virtualenv ${VENV_PATH}';. ${VENV_PATH}/bin/activate; bash -c 'set -ex;set -ex;${cmd.stripIndent()}'"
    return sh(script: script, returnStdout: returnStdout)
}

def run_cmd_stdout(cmd) {
    return run_cmd(cmd, true)
}

node ("${NODE_NAME}") {
  try {

    stage("Clean the environment") {
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

    stage("Clone tcp-qa project and install requirements") {
        run_cmd("""\
        git clone https://github.com/Mirantis/tcp-qa.git ${env.WORKSPACE}
        #cd tcp-qa
        if [ -n "$TCP_QA_REFS" ]; then
            set -e
            git fetch https://review.gerrithub.io/Mirantis/tcp-qa $TCP_QA_REFS && git checkout FETCH_HEAD || exit \$?
        fi
        pip install --upgrade --upgrade-strategy=only-if-needed -r tcp_tests/requirements.txt
        """)
    }

    // load shared methods from the clonned tcp-qa repository.
    // DO NOT MOVE this code before clonning the repo
    def rootDir = pwd()
    def shared = load "${rootDir}/tcp_tests/templates/SharedPipeline.groovy"

    stage("Create an environment ${ENV_NAME} in disabled state") {
        // do not fail if environment doesn't exists
        run_cmd("""\
        python ./tcp_tests/utils/create_devops_env.py
        """)
    }

    stage("Generate the model") {
        shared.generate_cookied_model()
    }

    stage("Generate config drive ISO") {
        shared.generate_configdrive_iso()
    }

    stage("Upload generated config drive ISO into volume on cfg01 node") {
        run_cmd("""\
        virsh vol-upload ${ENV_NAME}_cfg01.${LAB_CONFIG_NAME}.local_config /home/jenkins/images/${CFG01_CONFIG_IMAGE_NAME} --pool default
        virsh pool-refresh --pool default
        """)
    }

    stage("Run the 'underlay' and 'salt-deployed' fixtures to bootstrap salt cluster") {
        run_cmd("""\
        export MANAGER=devops
        export SHUTDOWN_ENV_ON_TEARDOWN=false
        export BOOTSTRAP_TIMEOUT=900
        export PYTHONIOENCODING=UTF-8
        export REPOSITORY_SUITE=${MCP_VERSION}
        #export SALT_STEPS_PATH=templates/${LAB_CONFIG_NAME}/salt.yaml
        export TEST_GROUP=test_install_local_salt
        py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -k \${TEST_GROUP}
        sleep 60  # wait for jenkins to start and IO calm down

        """)
    }

    stage("Run Jenkins job on salt-master [deploy_openstack:core]") {
        shared.run_job_on_day01_node("core")
    }

    stage("Run Jenkins job on salt-master [deploy_openstack:cicd]") {
        shared.run_job_on_day01_node("cicd")
    }

    for (stack in "${STACK_INSTALL}".split(",")) {
        stage("Run Jenkins job on CICD [deploy_openstack:${stack}]") {
            shared.run_job_on_cicd_nodes(stack)
        }
    }

    stage("Run tests") {
        run_cmd("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_k8s

            # Initialize variables used in tcp-qa tests
            export CURRENT_SNAPSHOT=sl_deployed  # provide the snapshot name required by the test
            export TESTS_CONFIGS=\$(pwd)/${ENV_NAME}_salt_deployed.ini  # some SSH data may be filled separatelly

            export MANAGER=empty  # skip 'hardware' fixture, disable snapshot/revert features
            # export SSH='{...}'  # non-empty SSH required to skip 'underlay' fixture. It is filled from TESTS_CONFIGS now
            export salt_master_host=\$SALT_MASTER_IP  # skip salt_deployed fixture
            export salt_master_port=6969
            export SALT_USER=\$SALTAPI_USER
            export SALT_PASSWORD=\$SALTAPI_PASS
            export COMMON_SERVICES_INSTALLED=true  # skip common_services_deployed fixture
            export K8S_INSTALLED=true              # skip k8s_deployed fixture
            export sl_installed=true              # skip sl_deployed fixture

            py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -m k8s_calico_sl

            #dos.py suspend ${ENV_NAME}
            #dos.py snapshot ${ENV_NAME} test_completed
            #dos.py resume ${ENV_NAME}
            #dos.py time-sync ${ENV_NAME}
            """)
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
      throw e
  } finally {
    // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
    // and report appropriate data to TestRail
    run_cmd("""\
        dos.py destroy ${ENV_NAME}
    """)
  }
}