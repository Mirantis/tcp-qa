#!/bin/bash

. /home/jenkins/fuel-devops30/bin/activate
pip install -r ./tcp_tests/requirements.txt -U
pip install psycopg2

export ENV_NAME=virtual-mcp-ocata-ceph-offline
export VENV_PATH=/home/jenkins/fuel-devops30
export IMAGE_PATH1604=/home/jenkins/images/xenial-server-cloudimg-amd64.qcow2
export SHUTDOWN_ENV_ON_TEARDOWN=false
export PYTHONIOENCODING=UTF-8
export LAB_CONFIG_NAME=virtual-mcp-ocata-ceph-offline
export CLUSTER_NAME=virtual-mcp-ocata-ovs-ceph-local
export REPOSITORY_SUITE=stable
export DISTROS_CODENAME=xenial
export SALT_VERSION=2016.3

export TEST_GROUP=test_ocata_ceph_all_ovs_install
export RUN_TEMPEST=true

# Offline deploy parameters
export SALT_MODELS_REF_CHANGE=refs/changes/86/13886/9

export BOOTSTRAP_TIMEOUT=1200

export HOST_APT=10.170.0.242
export HOST_SALTSTACK=10.170.0.242
export HOST_ARCHIVE_UBUNTU=10.170.0.242
export HOST_MIRROR_MCP_MIRANTIS=10.170.0.242
export HOST_MIRROR_FUEL_INFRA=10.170.0.242
export HOST_PPA_LAUNCHPAD=10.170.0.242

export SALT_MODELS_SYSTEM_REPOSITORY=https://gerrit.mcp.mirantis.local.test/salt-models/reclass-system
export SALT_FORMULAS_REPO=https://gerrit.mcp.mirantis.local.test/salt-formulas
export FORMULA_REPOSITORY="deb [arch=amd64] http://apt.mirantis.local.test/ubuntu-xenial ${REPOSITORY_SUITE} salt extra"
export FORMULA_GPG="http://apt.mirantis.local.test/public.gpg"
export SALT_REPOSITORY = "deb [arch=amd64] http://mirror.mirantis.local.test/" + REPOSITORY_SUITE+ "/saltstack-" + SALT_VERSION+ "/${DISTRIB_CODENAME} ${DISTRIB_CODENAME} main"

export SALT_REPOSITORY="deb [arch=amd64] http://apt.mirantis.local.test/ubuntu-xenial/ ${REPOSITORY_SUITE} salt/2016.3 main"
export SALT_GPG="http://apt.mirantis.local.test/public.gpg"
export UBUNTU_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/ubuntu xenial main universe restricted"
export UBUNTU_UPDATES_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/ubuntu xenial-updates main universe restricted"
export UBUNTU_SECURITY_REPOSITORY="deb http://mirror.mcp.mirantis.local.test/ubuntu xenial-security main universe restricted"

cd tcp_tests
py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -k ${TEST_GROUP}
