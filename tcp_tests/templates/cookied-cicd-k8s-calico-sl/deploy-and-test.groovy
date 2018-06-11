common = new com.mirantis.mk.Common()
shared = new tcp_tests.templates.SharedPipeline()

node ("${NODE_NAME}") {

    stage("test") {
        shared.print_some()
    }
}