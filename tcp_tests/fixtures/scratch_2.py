from tcp_tests.managers.jenkins.client import JenkinsClient
url="https://10.6.0.80:8081"
passw="7eQ11sE7ZyNqxVtWRQ2dhVmehvzg0nxY"
user="admin"

jenkins = JenkinsClient(url, user, passw)\

latest_build = jenkins.job_info('cvp-sanity')['lastCompletedBuild']['number']

print latest_build
report = jenkins.get_build_test_report(
    'cvp-sanity',
    latest_build
)
print "failCount", report.get("failCount")
print "passCount", report.get("passCount")

print jenkins.job_info('cvp-sanity')