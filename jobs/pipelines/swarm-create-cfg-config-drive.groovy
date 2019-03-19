import java.text.SimpleDateFormat

def gerrit = new com.mirantis.mk.Gerrit()
def dateFormat = new SimpleDateFormat("yyyyMMddHHmm")
def date = new Date()
def common_scripts_commit = "${COMMON_SCRIPTS_COMMIT}"
def iso_name = "${CONFIG_DRIVE_ISO_NAME}" ?: "cfg01.${CLUSTER_NAME}-config-${dateFormat.format(date)}.iso"
def node_name = "${NODE_NAME}"

def smc = [:]
smc['SALT_MASTER_MINION_ID'] = "cfg01.${CLUSTER_NAME}.local"
smc['SALT_MASTER_DEPLOY_IP'] = "${SALT_MASTER_DEPLOY_IP}"
smc['DEPLOY_NETWORK_GW'] = "${DEPLOY_NETWORK_GW}"
smc['DEPLOY_NETWORK_NETMASK'] = "${DEPLOY_NETWORK_NETMASK}"
smc['DEPLOY_NETWORK_MTU'] = "${DEPLOY_NETWORK_MTU}"
smc['DNS_SERVERS'] = "${DNS_SERVERS}"
smc['PIPELINES_FROM_ISO'] = '${PIPELINES_FROM_ISO}'
smc['PIPELINE_REPO_URL'] = '${PIPELINE_REPO_URL}'
smc['MCP_VERSION'] = "${MCP_VERSION}"
// smc['LOCAL_REPOS'] = 'true'
smc['MCP_SALT_REPO_KEY'] = "${MCP_SALT_REPO_KEY}"
smc['MCP_SALT_REPO_URL'] = "${MCP_SALT_REPO_URL}"

def entries(m) {
    m.collect {k, v -> [k, v]}
}

node (node_name) {

  timestamps(){

    stage("Clean Workspace") {
        step([$class: 'WsCleanup'])
    }

    stage("Get mk-pipelines, pipeline-library and mcp-common-scripts repositories") {
        def cloned = true
        withCredentials([[$class: 'SSHUserPrivateKeyBinding',
                          keyFileVariable: "GERRIT_KEY",
                          credentialsId: env.GERRIT_MCP_CREDENTIALS_ID,
                          usernameVariable: "GERRIT_USERNAME",
                          passwordVariable: "GERRIT_PASSWORD"]]) {

            sh ("""\
                set -ex
                eval \$(ssh-agent)
                ssh-add ${GERRIT_KEY}
                git clone ssh://${GERRIT_USERNAME}@gerrit.mcp.mirantis.net:29418/mcp/mcp-common-scripts mcp-common-scripts-git
                git clone --mirror ssh://${GERRIT_USERNAME}@gerrit.mcp.mirantis.net:29418/mk/mk-pipelines mk-pipelines
                git clone --mirror ssh://${GERRIT_USERNAME}@gerrit.mcp.mirantis.net:29418/mcp-ci/pipeline-library pipeline-library
            """)

            if (COMMON_SCRIPTS_COMMIT != '') {
                sh ("""\
                    set -ex
                    cd mcp-common-scripts-git
                    git checkout ${COMMON_SCRIPTS_COMMIT}
                    git log -1
                """)
            }

            if (MCP_COMMON_SCRIPTS_REFS != '') {
                sh ("""\
                    set -ex
                    eval \$(ssh-agent)
                    ssh-add ${GERRIT_KEY}
                    cd mcp-common-scripts-git
                    git fetch ssh://${GERRIT_USERNAME}@gerrit.mcp.mirantis.com:29418/mcp/mcp-common-scripts ${MCP_COMMON_SCRIPTS_REFS} && git checkout FETCH_HEAD
                    git log -1
                """)
            }

            if (PIPELINE_LIBRARY_REF != '') {
                sh ("""\
                    set -ex
                    eval \$(ssh-agent)
                    ssh-add ${GERRIT_KEY}
                    cd pipeline-library
                    git fetch https://gerrit.mcp.mirantis.net/mcp-ci/pipeline-library ${PIPELINE_LIBRARY_REF}
                    git tag ${MCP_VERSION} FETCH_HEAD -f
                    git branch -f release/${MCP_VERSION} FETCH_HEAD
                    git log -1
                """)
            }
            if (MK_PIPELINES_REF != '') {
                sh ("""\
                    set -ex
                    eval \$(ssh-agent)
                    ssh-add ${GERRIT_KEY}
                    cd mk-pipelines
                    git fetch https://gerrit.mcp.mirantis.net/mcp-ci/mk-pipelines ${MK_PIPELINES_REF}
                    git tag ${MCP_VERSION} FETCH_HEAD -f
                    git branch -f release/${MCP_VERSION} FETCH_HEAD
                    git log -1
                """)
            }

        }
    }

    stage("Get cluster model") {
        def model_url = "${MODEL_URL}"
        sh "rm -rf model"
        if (MODEL_URL_OBJECT_TYPE == 'tar.gz') {
            sh "wget -O model.tar.gz '${model_url}'"
            sh "mkdir model && cd model && tar zxfv ../model.tar.gz"
        } else {
            sh "git clone --recursive $model_url -b ${MCP_VERSION} model"
            // remove .git file with absolute path and re-init the file with relative path
            sh "rm model/classes/system/.git"
            sh "cd model && git submodule update"
        }
    }

    stage("Prepare arguments for generation config drive") {

        config_drive_script_path = "mcp-common-scripts-git/config-drive/create_config_drive.sh"
        user_data_script_path = "mcp-common-scripts-git/config-drive/master_config.yaml"
        sh "chmod +x ${config_drive_script_path}"

        //args = "--user-data user_data --vendor-data user_data2 --hostname cfg01 --model model --mk-pipelines mk-pipelines/ --pipeline-library pipeline-library/ ${iso_name}"
        args = "--user-data user_data2 --vendor-data ${user_data_script_path} --hostname cfg01 --model model --mk-pipelines mk-pipelines/ --pipeline-library pipeline-library/"
        try {
            sh "test -f model/encryption-key.asc"
            args = "${args} --gpg-key model/encryption-key.asc ${iso_name}"

        } catch (e) {
            args = "${args} ${iso_name}"
        }
    }

    stage("Set data"){
        for (i in entries(smc)) {
            // Replace only if the variable is non-empty, leave default otherwise
            if (i[1]) {
                sh "sed -i \"s,export ${i[0]}=.*,export ${i[0]}=${i[1]},\" ${user_data_script_path}"
            }
        }
    }

    stage("Create user_data2"){
        //http://jen20.com/2015/10/04/cloudconfig-merging.html
        //TODO(ddmitriev): allow to read such file from
        //   ./tcp_tests/templates/${LAB_CONFIG_NAME}/ directory for each lab
        def user_data2 = """\
#cloud-config, see http://cloudinit.readthedocs.io/en/latest/topics/examples.html

#write_files:   # write_files don't work as expected because overwrites this key from mcp-common-scripts YAML, losing data
#  - path: /etc/default/grub.d/97-enable-grub-menu.cfg
#    content: |
#      GRUB_RECORDFAIL_TIMEOUT=30
#      GRUB_TIMEOUT=10
#      GRUB_TIMEOUT_STYLE=menu
#
#  - path: /root/interfaces
#    content: |
#      auto lo
#      iface lo inet loopback
#
#      auto ens3
#      iface ens3 inet dhcp
#
#  - path: /root/.ssh/config
#    owner: root:root
#    permissions: '0600'
#    content: |
#      Host *
#        ServerAliveInterval 60
#        ServerAliveCountMax 0
#        StrictHostKeyChecking no
#        UserKnownHostsFile /dev/null
#
#  - path: /etc/cloud/master_environment_override
#    owner: root:root
#    permissions: '0600'
#    content: |
#      export SALT_MASTER_MINION_ID="cfg01.${CLUSTER_NAME}.local"
#      export SALT_MASTER_DEPLOY_IP="${SALT_MASTER_DEPLOY_IP}"
#      export DEPLOY_NETWORK_GW="${DEPLOY_NETWORK_GW}"
#      export DEPLOY_NETWORK_NETMASK="${DEPLOY_NETWORK_NETMASK}"
#      export DNS_SERVERS="${DNS_SERVERS}"
#      export PIPELINES_FROM_ISO="${PIPELINES_FROM_ISO}"
#      export PIPELINE_REPO_URL="${PIPELINE_REPO_URL}"
#      export MCP_VERSION="${MCP_VERSION}"
#      export LOCAL_REPOS="true"
#      export MCP_SALT_REPO_KEY="${MCP_SALT_REPO_KEY}"
#      export MCP_SALT_REPO_URL="${MCP_SALT_REPO_URL}"

output:
  all: '| tee -a /var/log/cloud-init-output.log /dev/tty0'

ssh_pwauth: True
users:
   - name: root
     sudo: ALL=(ALL) NOPASSWD:ALL
     shell: /bin/bash

disable_root: false
chpasswd:
   list: |
    root:r00tme
   expire: False

bootcmd:
   # Block access to SSH while node is preparing
   - cloud-init-per once sudo touch /is_cloud_init_started
   # Enable root access
   - sed -i -e '/^PermitRootLogin/s/.*/PermitRootLogin yes/' /etc/ssh/sshd_config
   - service sshd restart

merge_how: "dict(recurse_array)+list(append)"
"""
    writeFile(file: "user_data2", text: user_data2, encoding: "UTF-8")
    }

    stage("Create config-drive"){
      // create cfg config-drive
      // apt package genisoimage is required for this stage
      sh "./${config_drive_script_path} ${args}"
    }

    stage("Save artifacts") {
        archiveArtifacts allowEmptyArchive: false,
            artifacts: "${iso_name}"
    }

    stage("Download config drive to slave") {
        if (DOWNLOAD_CONFIG_DRIVE == 'true') {
            println "Remove previous config drive ISO"
            sh("""\
                rm /home/jenkins/images/${iso_name} || true
            """)

            def b_res = build job: 'download-config-drive',
                parameters: [
                        string(name: 'IMAGE_URL', value: "${BUILD_URL}/artifact/${iso_name}"),
                        string(name: 'NODE_NAME', value: "${NODE_NAME}")
                    ]
        } else {
            echo "Drive only generated. But didn't download"
        }
    }
  }
}
