#!/bin/bash

. ${VENV_PATH}/bin/activate

tar_name=$(find $(pwd) -name ${TEST_GROUP}"*.tar.gz")
if [ -n "$tar_name" ]; then
    rm $tar_name
fi

d_name=$(find $(pwd) -name "date.txt")
if [ -n "$d_name" ]; then
    rm $d_name
fi
DATE=$(date +%Y-%m-%d)
echo $DATE >> date.txt

report_name=$(find $(pwd) -name "report_*.xml")

if [ -n "$report_name" ]; then
    rm $report_name
fi

report_name_html=$(find $(pwd) -name "report_*.html")

if [ -n "$report_name_html" ]; then
    rm $report_name_html
fi

pip install -U -r tcp_tests/requirements.txt

dos.py erase $ENV_NAME || true

#PYTHONPATH=".:$PATH" python tcp_tests/run_test.py -k ${TEST_GROUP}
cd tcp_tests

echo "Using DAY01 image: $(cat ${IMAGE_PATH_CFG01_DAY01}.md5)"

py.test -vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml -k ${TEST_GROUP}
