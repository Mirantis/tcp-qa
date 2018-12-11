#!/bin/bash

. ${REPORT_VENV_PATH}/bin/activate
d=$(cat date.txt)
cd tcp_tests
report --verbose --testrail-run-update \
    --testrail-url https://mirantis.testrail.com \
    --testrail-user "$TR_USERNAME" \
    --testrail-password "$TR_PASSWORD" \
    --testrail-project "Mirantis Cloud Platform" \
    --testrail-plan-name "[MCP-Q2]System-"$REPOSITORY_SUITE"-"$d \
    --env-description $ENV_NAME \
    --testrail-milestone "MCP1.1" \
    --testrail-suite "[MCP_X] integration cases" \
    --xunit-name-template '{methodname}' \
    --testrail-name-template '{title}' nosetests.xml