import groovy.json.JsonSlurperClassic
import java.text.SimpleDateFormat

def dateFormat = new SimpleDateFormat("yyyyMMddHHmm")
def date = new Date()

timeout(time: 720, unit: 'MINUTES') {
timestamps(){ node(NODE) {
    stage("Cleanup workspace") {
        if (!params.TEST_GROUP) {
           throw new Exception("TEST_GROUP parameter is mandatory")

        }
        step([$class: 'WsCleanup'])
    }
    try {
        stage("Clone tcp-qa") {
            git url: "https://github.com/Mirantis/tcp-qa"
        }
        stage("Run tests") {
            sh "jobs/scripts/run_tcp_qa.sh"
        }
    } catch(error) {
        throw error
    } finally {
        stage("Save artifacts") {
            archiveArtifacts allowEmptyArchive: false,
                artifacts: "tcp_tests/*.ini, tcp_tests/*.log,**/nosetests.xml,**/report*.xml,**/*.tar.gz"
        }
        stage("Destory environment") {
            sh ". ${VENV_PATH}/bin/activate; dos.py destroy \$ENV_NAME"
        }
        stage("Collect reports") {
            sh "jobs/scripts/run_tr_report.sh"
        }
    }
}}
}