node('cz8133') {
    stage("Checkout review") {
        checkout(
            [$class: 'GitSCM',
             branches: [[name: "${GERRIT_BRANCH}"]],
             doGenerateSubmoduleConfigurations: false,
             extensions: [[$class: 'CleanBeforeCheckout']],
             submoduleCfg: [],
             userRemoteConfigs:
             [[refspec: "${GERRIT_REFSPEC}",
               url: 'https://review.gerrithub.io/Mirantis/tcp-qa']]])

    }
    stage("run Gradle tests") {
      sh "/gradlew test"
    }
}
