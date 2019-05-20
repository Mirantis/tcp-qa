#!/bin/bash -xe

DEVOPS_VENV_PATH=/home/jenkins/fuel-devops30
REPORT_VENV_PATH=/home/jenkins/venv_testrail_reporter

if [ ! -d ${DEVOPS_VENV_PATH} ]; then
    virtualenv ${DEVOPS_VENV_PATH}
fi
if [ ! -d ${REPORT_VENV_PATH} ]; then
    virtualenv ${REPORT_VENV_PATH}
fi

# Install tcp-qa requirements
. ${DEVOPS_VENV_PATH}/bin/activate
pip install -r https://raw.githubusercontent.com/Mirantis/tcp-qa/master/tcp_tests/requirements.txt
pip install psycopg2  # workaround for setup with PostgreSQL , to keep requirements.txt for Sqlite3 only

# Install xunit2testrail
. ${REPORT_VENV_PATH}/bin/activate
#pip install xunit2testrail -U
pip install git+https://github.com/dis-xcom/testrail_reporter -U  # Removed accessing to an unexisting pastebin on srv62

chown -R jenkins:jenkins /home/jenkins/
