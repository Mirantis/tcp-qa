#!/bin/bash


#. /root/keystonercv3

#heat -v --debug stack-create teststack \
#  --template-file ../cookied-cicd-queens-dvr-sl/underlay.hot \
#  --environment-file microcloud-8116.env \
#  --parameters keypair=baremetal

set -ex

cd $(pwd)/../../../
export PYTHONIOENCODING=UTF-8
export PYTHONPATH=$(pwd)

export IMAGE_PATH1604=/home/jenkins/images/ubuntu-16-04-x64-mcp2019.2.0.qcow2
export IMAGE_PATH_CFG01_DAY01=/home/jenkins/images/cfg01-day01.qcow2
export REPOSITORY_SUITE=2019.2.0

export MANAGER=heat

export ENV_NAME=test_env_queens
export LAB_CONFIG_NAME=cookied-cicd-queens-dvr-sl

export OS_AUTH_URL=https://10.90.0.80:5000/v3
export OS_USERNAME=admin
export OS_PASSWORD=sacLMXAucxABoxT3sskVRHMbKuwa1ZIv
export OS_PROJECT_NAME=admin

#export TEST_GROUP=test_create_environment
export TEST_GROUP=test_bootstrap_salt
py.test -vvv -s -p no:django -p no:ipdb --junit-xml=deploy_hardware.xml -k ${TEST_GROUP}
#dos.py start test-lab-for-ironic
