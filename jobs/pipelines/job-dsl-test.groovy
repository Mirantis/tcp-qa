import java.text.SimpleDateFormat

def dateFormat = new SimpleDateFormat("yyyyMMddHHmm")
def date = new Date()

ansiColor('xterm') { timestamps() { node('cz8133') {

    step([$class: 'WsCleanup'])
    stage("Checkout review") {
        checkout(
            [$class: 'GitSCM',
             branches: [[name: "${GERRIT_REFSPEC}"]],
             doGenerateSubmoduleConfigurations: false,
             extensions: [[$class: 'CleanBeforeCheckout']],
             submoduleCfg: [],
             userRemoteConfigs:
             [[refspec: "+${GERRIT_REFSPEC}:refs/remotes/origin/${GERRIT_REFSPEC} +refs/heads/*:refs/remotes/origin/*",
               url: 'https://review.gerrithub.io/Mirantis/tcp-qa']]])

    }
    stage("run Gradle tests") {
        sh "./gradlew test -i"
    }
    stage("Collect artifacts") {
        archiveArtifacts allowEmptyArchive: false,
            artifacts: "build/reports/**/*.*,build/test-results/**/*.xml"
        step([$class: 'XUnitBuilder',
            testTimeMargin: '3000',
            thresholdMode: 1,
            thresholds: [
              [$class: 'FailedThreshold',
                failureThreshold: '0'],
              [$class: 'SkippedThreshold',
                failureThreshold: '0']],
            tools: [
              [$class: 'JUnitType',
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: 'build/test-results/**/*.xml',
                skipNoTestFiles: false,
                stopProcessingIfError: false]]])
    }
}}}
