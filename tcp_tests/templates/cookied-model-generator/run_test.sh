#!/bin/bash

. /home/jenkins/fuel-devops30/bin/activate

export ENV_NAME=model-generator
export VENV_PATH=/home/jenkins/fuel-devops30
export ERASE_EXISTING_ENVIRONMENT=false
export #ERASE_EXISTING_ENVIRONMENT=true
#export IMAGE_PATH1604=/home/jenkins/images/xenial-server-cloudimg-amd64.qcow2
#export IMAGE_PATH1604=/home/jenkins/images/cfg01-day01.qcow2
export CFG01_DAY01_VOLUME_NAME=cfg01-day01.qcow2
export #SHUTDOWN_ENV_ON_TEARDOWN=true
export SHUTDOWN_ENV_ON_TEARDOWN=false
export PYTHONIOENCODING=UTF-8
export REPOSITORY_SUITE=testing

export LAB_CONFIG_NAME=cookied-model-generator
export LAB_CONTEXT_NAME=cookied-mcp-ocata-dop-sl2
#export LAB_CONTEXT_NAME=cookied-mcp-ocata-dvr-vxlan
#export LAB_CONTEXT_NAME=cookied-bm-mcp-dvr-vxlan
#export LAB_CONTEXT_NAME=cookied-bm-mcp-ocata-contrail
export DOMAIN_NAME=${LAB_CONTEXT_NAME}.local
export SALT_STEPS_PATH=templates/${LAB_CONFIG_NAME}/salt_${LAB_CONTEXT_NAME}.yaml

#export TEST_GROUP=test_failover_openstack_services
export TEST_GROUP=test_generate_model

export STORAGE_POOL_NAME=second_pool

export MAKE_SNAPSHOT_STAGES=false

dos.py erase ${ENV_NAME}

cd tcp_tests
py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -k ${TEST_GROUP}
