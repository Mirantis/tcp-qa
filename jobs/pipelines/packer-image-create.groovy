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
                shared.update_working_dir()
                sh "mkdir ./tmp"
            }

            def packer_zipname = "packer.zip"
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
                    sh "unzip ${packer_zipname}"
                }
            }

            stage("Build the cloudinit ISO") {
                // Check that genisoimage is installed, or try to install it
                sh "which genisoimage || sudo apt-get -y install genisoimage"
                // Generate config-drive ISO
                sh "mkisofs -o ${configdrive_isoname} -V cidata -r -J --quiet ${BUILD_CONFIG_DRIVE_PATH}"
            }

            stage("Build the image '${IMAGE_NAME}'") {
                // Remove the image if exists
                sh "rm -f ${build_image_path} || true"
                // Build the image
                sh (script: """\
                    set -ex;
                    PACKER_LOG=1;
                    TMPDIR=${env.WORKSPACE}/tmp;
                    PACKER_IMAGES_CACHE=\${TMPDIR}/cache/
                    mkdir -p \${PACKER_IMAGES_CACHE}
                    packer build -machine-readable -parallel=false -only='qemu' ${BUILD_PACKER_CONFIG_PATH};
                """, returnStdout: true)
            }

            stage("Archive artifacts") {
                archiveArtifacts artifacts: "./tmp/*.qcow2"
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