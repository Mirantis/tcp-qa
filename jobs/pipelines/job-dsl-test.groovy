import javaposse.jobdsl.dsl.DslScriptLoader
import javaposse.jobdsl.dsl.MemoryJobManagement
import javaposse.jobdsl.dsl.ScriptRequest
import spock.lang.Specification

class TestJenkinsJobs extends Specification {

    @Shared
    @ClassRule
    private JenkinsRule jenkinsRule = new JenkinsRule()

    @Shared
    private File outputDir = new File('./build/debug-xml')

    def setupSpec() {
        outputDir.deleteDir()
    }

    @Unroll
    def 'test basic job configuration'() {
        given:
        URL scriptURL = new File('jobs/dsl').toURI().toURL()
        ScriptRequest scriptRequest = new ScriptRequest('runners.groovy', null, scriptURL)
        MemoryJobManagement jobManagement = new MemoryJobManagement()

        when:
        // GeneratedItems items = new DslScriptLoader(jm).runScript(file.text)
        DslScriptLoader.runDslEngine(scriptRequest, jobManagement)
        writeItems(jobManagement.savedConfigs, outputDir)

        then:
        noExceptionThrown()

    }

    /**
     * Write the config.xml for each generated job and view to the build dir.
     */
    private void writeItems(GeneratedItems items, File outputDir) {
        Jenkins jenkins = jenkinsRule.jenkins
        items.jobs.each { GeneratedJob generatedJob ->
            String jobName = generatedJob.jobName
            Item item = jenkins.getItemByFullName(jobName)
            String text = new URL(jenkins.rootUrl + item.url + 'config.xml').text
            TestUtil.writeFile(new File(outputDir, 'jobs'), jobName, text)
        }

        items.views.each { GeneratedView generatedView ->
            String viewName = generatedView.name
            View view = jenkins.getView(viewName)
            String text = new URL(jenkins.rootUrl + view.url + 'config.xml').text
            TestUtil.writeFile(new File(outputDir, 'views'), viewName, text)
        }
    }

}