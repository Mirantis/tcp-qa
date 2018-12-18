node('master') {
    stage("run Gradle tests") {
      sh "/gradlew test"
    }
}
