import java.text.SimpleDateFormat

def dateFormat = new SimpleDateFormat("yyyyMMddHHmm")
def date = new Date()
def common_scripts_commit = "${COMMON_SCRIPTS_COMMIT}"
def iso_name = "${CONFIG_DRIVE_ISO_NAME}" ?: "cfg01.${CLUSTER_NAME}-config-${dateFormat.format(date)}.iso"
def node_name = "${NODE_NAME}"


node (node_name) {

  timestamps(){

    stage("Clean Workspace") {
        step([$class: 'WsCleanup'])
    }

    stage("Get scripts") {
      // apt package genisoimage is required for this stage
      // download create-config-drive

      def config_drive_script_url = "https://raw.githubusercontent.com/Mirantis/mcp-common-scripts/${common_scripts_commit}/config-drive/create_config_drive.sh"
      sh "wget -O create-config-drive ${config_drive_script_url} && chmod +x create-config-drive"

      def user_data_script_url = "https://raw.githubusercontent.com/Mirantis/mcp-common-scripts/${common_scripts_commit}/config-drive/master_config.yaml"
      sh "wget -O user_data ${user_data_script_url}"
    }

    stage("Clone mk-pipelines and pipeline-library") {
        sh "git clone --mirror https://github.com/Mirantis/mk-pipelines.git -b ${MCP_VERSION} mk-pipelines"
        sh "git clone --mirror https://github.com/Mirantis/pipeline-library.git -b ${MCP_VERSION} pipeline-library"
        if (PIPELINE_LIBRARY_REF != '') {
           sh "cd pipeline-library; git fetch https://gerrit.mcp.mirantis.net/mcp-ci/pipeline-library ${PIPELINE_LIBRARY_REF} ; git tag ${MCP_VERSION} FETCH_HEAD -f ; cd .."
        }
        if (MK_PIPELINES_REF != '') {
           sh "cd mk-pipelines; git fetch https://gerrit.mcp.mirantis.net/mcp-ci/mk-pipelines ${MK_PIPELINES_REF} ; git tag ${MCP_VERSION} FETCH_HEAD -f; cd .."
        }
        args = "--user-data user_data --vendor-data user_data2 --hostname cfg01 --model model --mk-pipelines mk-pipelines/ --pipeline-library pipeline-library/ ${iso_name}"
    }

    stage("Get cluster model") {
        def model_url = "${MODEL_URL}"
        sh "rm -rf model"
        if (MODEL_URL_OBJECT_TYPE == 'tar.gz') {
            sh "wget -O model.tar.gz '${model_url}'"
            sh "mkdir model && cd model && tar zxfv ../model.tar.gz"
        } else {
            sh "git clone --recursive $model_url -b ${MCP_VERSION} model"
            // remove .git file with hardcoded path
            sh "rm model/classes/system/.git"
        }
    }

    // stage("Fetch model"){
    //   repo_url = "ssh://mos-scale-jenkins@gerrit.mirantis.com:29418/mos-scale/salt-models"
    //   sh "rm -rf model"
    //   sshagent (credentials: ['ece6c586-cd26-481c-92a8-ccae6bf9cf86']) {
    //     sh "git clone --recursive $repo_url model"
    //   }
    // }

    stage("Create user_data2"){
        //http://jen20.com/2015/10/04/cloudconfig-merging.html
        //TODO(ddmitriev): allow to read such file from
        //   ./tcp_tests/templates/${LAB_CONFIG_NAME}/ directory for each lab
        def user_data2 = """\
#cloud-config, see http://cloudinit.readthedocs.io/en/latest/topics/examples.html

write_files:
  - path: /etc/default/grub.d/97-enable-grub-menu.cfg
    content: |
      GRUB_RECORDFAIL_TIMEOUT=30
      GRUB_TIMEOUT=10
      GRUB_TIMEOUT_STYLE=menu

  - path: /root/interfaces
    content: |
      auto lo
      iface lo inet loopback

      auto ens3
      iface ens3 inet dhcp

  - path: /root/.ssh/config
    owner: root:root
    permissions: '0600'
    content: |
      Host *
        ServerAliveInterval 60
        ServerAliveCountMax 0
        StrictHostKeyChecking no
        UserKnownHostsFile /dev/null

  - path: /etc/cloud/master_environment_override
    owner: root:root
    permissions: '0600'
    content: |
      export SALT_MASTER_MINION_ID="cfg01.${CLUSTER_NAME}.local"
      export SALT_MASTER_DEPLOY_IP="${SALT_MASTER_DEPLOY_IP}"
      export DEPLOY_NETWORK_GW="${DEPLOY_NETWORK_GW}"
      export DEPLOY_NETWORK_NETMASK="${DEPLOY_NETWORK_NETMASK}"
      export DNS_SERVERS="${DNS_SERVERS}"
      export PIPELINES_FROM_ISO="${PIPELINES_FROM_ISO}"
      export PIPELINE_REPO_URL="${PIPELINE_REPO_URL}"
      export MCP_VERSION="${MCP_VERSION}"
      export LOCAL_REPOS="true"
      export MCP_SALT_REPO_KEY="${MCP_SALT_REPO_KEY}"
      export MCP_SALT_REPO_URL="${MCP_SALT_REPO_URL}"

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

runcmd:
    - touch /is_cloud_init_finished
    - sed -i -e '/^PermitRootLogin/s/.*/PermitRootLogin yes/' /etc/ssh/sshd_config

merge_how: "dict(recurse_array)+list(append)"
"""
    writeFile(file: "user_data2", text: user_data2, encoding: "UTF-8")
    }

    stage("Create config-drive"){
      // create cfg config-drive
      sh "./create-config-drive ${args}"
    }

    stage("Save artifacts") {
        archiveArtifacts allowEmptyArchive: false,
            artifacts: "${iso_name}"
    }

    stage("Download config drive to slave") {
        if (DOWNLOAD_CONFIG_DRIVE == 'true') {
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
