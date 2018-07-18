@Library('tcp-qa')_

common = new com.mirantis.mk.Common()
shared = new com.mirantis.system_qa.SharedPipeline()

node ("${NODE_NAME}") {
  try {

    stage("Clean the environment and clone tcp-qa") {
        shared.prepare_working_dir()
    }

    stage("Create environment, generate mode, bootstrap the salt-cluster") {
        shared.swarm_bootstrap_salt_cluster_devops()
    }

    // Install core and cicd
    stage("Run Jenkins job on salt-master [deploy_openstack:core]") {
        shared.run_job_on_day01_node("core")
    }

    stage("Run Jenkins job on salt-master [deploy_openstack:cicd]") {
        shared.run_job_on_day01_node("cicd")
    }

    // Install the cluster
    for (stack in "${PLATFORM_STACK_INSTALL}".split(",")) {
        stage("Run Jenkins job on CICD [deploy_openstack:${stack}]") {
            shared.run_job_on_cicd_nodes(stack)
        }
    }

    stage("Run tests") {
        shared.run_cmd("""\
            export ENV_NAME=${ENV_NAME}
            . ./tcp_tests/utils/env_salt
            . ./tcp_tests/utils/env_k8s

            # Initialize variables used in tcp-qa tests
            export CURRENT_SNAPSHOT=k8s_deployed  # provide the snapshot name required by the test
            export TESTS_CONFIGS=\$(pwd)/${ENV_NAME}_core_deployed.ini  # some SSH data may be filled separatelly

            export MANAGER=empty  # skip 'hardware' fixture, disable snapshot/revert features
            # export SSH='{...}'  # non-empty SSH required to skip 'underlay' fixture. It is filled from TESTS_CONFIGS now
            export salt_master_host=\$SALT_MASTER_IP  # skip core_deployed fixture
            export salt_master_port=6969
            export SALT_USER=\$SALTAPI_USER
            export SALT_PASSWORD=\$SALTAPI_PASS
            export COMMON_SERVICES_INSTALLED=true  # skip common_services_deployed fixture
            export K8S_INSTALLED=true              # skip k8s_deployed fixture

            py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -m k8s_calico
            """)
    }

  } catch (e) {
      common.printMsg("Job failed", "red")
      throw e
  } finally {
    // TODO(ddmitriev): analyze the "def currentResult = currentBuild.result ?: 'SUCCESS'"
    // and report appropriate data to TestRail
    shared.run_cmd("""\
        dos.py destroy ${ENV_NAME}
    """)
  }

}