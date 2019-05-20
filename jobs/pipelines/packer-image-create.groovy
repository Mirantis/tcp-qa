/**
 *
 * Deploy the product cluster using Jenkins master on CICD cluster
 *
 * Expected parameters:

 *   PACKER_URL
 *   PACKER_ZIP_MD5

 *   BUILD_CONFIG_DRIVE_PATH
 *   BUILD_PACKER_CONFIG_PATH
 *   BASE_IMAGE_URL
 *   BASE_IMAGE_MD5

 *   OS_AUTH_URL                   OpenStack keystone catalog URL
 *   OS_PROJECT_NAME               OpenStack project (tenant) name
 *   OS_USER_DOMAIN_NAME           OpenStack user domain name
 *   OS_CREDENTIALS                OpenStack username and password credentials ID in Jenkins
 *   UPLOAD_IMAGE_TO_GLANCE        If True: upload image to glance; if False: store as an artifact

 *   IMAGE_NAME
 */

@Library('tcp-qa')_

def common = new com.mirantis.mk.Common()
def shared = new com.mirantis.system_qa.SharedPipeline()

timeout(time: 6, unit: 'HOURS') {
    node () {
        try {

            stage("Clean the environment and clone tcp-qa") {
                deleteDir()
                shared.run_cmd("""\
                    git clone https://github.com/Mirantis/tcp-qa.git ${WORKSPACE}
                """)
                shared.update_working_dir(false)
                sh "mkdir ./tmp"
            }

            def packer_zipname = "/tmp/packer.zip"
            def configdrive_isoname = "./tmp/config-drive.iso"

            stage("Prepare Packer") {
                // Check that the archive is already downloaded and has a correct checksum. Remove if not match
                if (fileExists(packer_zipname)) {
                    sh(script: "bash -cex 'md5sum -c --status <(echo ${PACKER_ZIP_MD5} ${packer_zipname})' || rm -f ${packer_zipname}", returnStdout: true)
                }
                // If the file is missing or removed, then download it and check the checksum
                if (!fileExists(packer_zipname)) {
                    sh(script: "wget --quiet -O ${packer_zipname} ${PACKER_URL}", returnStdout: true)
                    // Should fail the job if not match
                    sh(script: "bash -cex 'md5sum -c --status <(echo ${PACKER_ZIP_MD5} ${packer_zipname})'", returnStdout: true)
                }
                sh "unzip ${packer_zipname}"
            }

            stage("Build the cloudinit ISO") {
                // Check that genisoimage is installed, or try to install it
                sh "which genisoimage || sudo apt-get -y install genisoimage"
                // Generate config-drive ISO
                sh "mkisofs -o ${configdrive_isoname} -V cidata -r -J --quiet ${BUILD_CONFIG_DRIVE_PATH}"
            }

            stage("Build the image '${IMAGE_NAME}'") {
                // Build the image
                sh (script: """\
                    set -ex;
                    export PACKER_LOG=1;
                    export PACKER_CACHE_DIR='/tmp/packer_cache_${IMAGE_NAME}/';
                    mkdir -p \${PACKER_CACHE_DIR};
                    ./packer build -machine-readable -parallel=false -only='qemu' ${BUILD_PACKER_CONFIG_PATH};
                """, returnStdout: true)
            }


            if (env.UPLOAD_IMAGE_TO_GLANCE) {

                stage("Upload generated config drive ISO into volume on cfg01 node") {
                    withCredentials([
                       [$class          : 'UsernamePasswordMultiBinding',
                       credentialsId   : env.OS_CREDENTIALS,
                       passwordVariable: 'OS_PASSWORD',
                       usernameVariable: 'OS_USERNAME']
                    ]) {
                        env.OS_IDENTITY_API_VERSION = 3

                        def imagePath = "tmp/${IMAGE_NAME}/${IMAGE_NAME}.qcow2"
                        shared.run_cmd("""\
                            openstack --insecure image delete ${IMAGE_NAME} || true
                            sleep 3
                            openstack --insecure image create ${IMAGE_NAME} --file ${imagePath} --disk-format qcow2 --container-format bare
                        """)
                    }
                }
            } else {

                stage("Archive artifacts") {
                    archiveArtifacts artifacts: "tmp/${IMAGE_NAME}/${IMAGE_NAME}.qcow2"
                }
            }

        } catch (e) {
            common.printMsg("Job is failed", "purple")
            throw e
        } finally {
            // Remove the image after job is finished
            sh "rm -f ./tmp/${IMAGE_NAME}.qcow2 || true"
        } // try
    } // node
} // timeout