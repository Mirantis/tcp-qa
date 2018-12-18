

def jobs = [
    [
        name: "cookied-cicd-k8s-genie",
    ],
    [
        name: "cookied-cicd-k8s-calico"
    ],
    [
        name: "cookied-cicd-pike-dvr-sl"
    ],
    [
        name: "cookied-cicd-pike-ovs-sl"
    ],
    [
        name: "cookied-cicd-k8s-calico-sl"
    ],
    [
        name: "cookied-cicd-pike-dvr-ceph"
    ],
    [
        name: "cookied-cicd-queens-dvr-sl"
    ],
]


for (j in jobs) {
    job("runner-${j.name}") {
        description '''Workaround for https://issues.jenkins-ci.org/browse/JENKINS-38825
Make possibly to run pipeline-based jobs from multijob.'''
        label('cz8133')
        weight(1)

        steps {
            downstreamParameterized {
                trigger("${j.name}") {
                    block {
                        buildStepFailure('FAILURE')
                        failure('FAILURE')
                        unstable('UNSTABLE')
                    }
                }
            }
        }



    }
}