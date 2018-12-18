node('cz8133') {
    stage("run Gradle tests") {
      sh "/gradlew test"
    }
}
