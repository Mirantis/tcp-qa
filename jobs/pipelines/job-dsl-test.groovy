node('cz8133') {
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
        dir("${pwd}/tcp_tests"){
            sh "./gradlew test"
        }
    }
}
