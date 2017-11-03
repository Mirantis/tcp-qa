#!/bin/bash

set -ex

export PYTHONIOENCODING=UTF-8
export PYTHONPATH=$(pwd)

export IMAGE_PATH1604=/home/jenkins/images/ubuntu-16-04-x64-mcp2019.2.0.qcow2
export IMAGE_PATH_CFG01_DAY01=/home/jenkins/images/cfg01-day01.qcow2
export REPOSITORY_SUITE=2019.2.0

export MANAGER=heat

export TEST_GROUP=test_create_environment
export ENV_NAME=test_env_queens
export LAB_CONFIG_NAME=cookied-cicd-queens-dvr-sl



#export OS_IDENTITY_API_VERSION=3
#export OS_AUTH_URL=http://10.60.0.100:35357/v3
#export OS_PROJECT_DOMAIN_NAME=Default
#export OS_USER_DOMAIN_NAME=Default
#export OS_PROJECT_NAME=admin
#export OS_TENANT_NAME=admin
#export OS_USERNAME=admin
#export OS_PASSWORD=sacLMXAucxABoxT3sskVRHMbKuwa1ZIv
#export OS_REGION_NAME=RegionOne
#export OS_INTERFACE=internal
#export OS_ENDPOINT_TYPE="internal"
#export OS_CACERT="/etc/ssl/certs/ca-certificates.crt"

#export HEAT_VERSION=3
export OS_AUTH_URL=https://10.90.0.80:5000/v3
#export OS_USERNAME=system-ci
#export OS_PASSWORD=system-ci-1234
#export OS_PROJECT_NAME=testproject
export OS_STACK_NAME=$ENV_NAME

export OS_USERNAME=admin
export OS_PASSWORD=sacLMXAucxABoxT3sskVRHMbKuwa1ZIv
export OS_PROJECT_NAME=admin


py.test -vvv -s -p no:django -p no:ipdb --junit-xml=deploy_hardware.xml -k ${TEST_GROUP}
#dos.py start test-lab-for-ironic
