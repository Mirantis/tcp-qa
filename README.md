# tcp-qa

Default template used here requires 20 vCPU and 52Gb host RAM.

Clone the repo
--------------

git clone https://github.com/Mirantis/tcp-qa

cd ./tcp-qa

Install requirements
--------------------

pip install -r ./tcp_tests/requirements.txt

Initialize fuel-devops database if needed:
------------------------------------------

dos-manage.py migrate

Get cloudinit image
-------------------

wget https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img -O ./trusty-server-cloudimg-amd64.qcow2

Export variables
----------------

export ENV_NAME=tcpcloud-mk20  # Optional

export IMAGE_PATH=./trusty-server-cloudimg-amd64.qcow2

Run deploy test
-----------------------------------------
export WORKSPACE=$(pwd)
export SUSPEND_ENV_ON_TEARDOWN=false  # Optional

py.test -vvv -s -k test_tcp_install_default


Create and start the env for manual tests
-----------------------------------------

dos.py create-env ./tcpcloud-wk20.yaml

dos.py start "${ENV_NAME}"


Then, wait until cloud-init is finished and port 22 is open (~3-4 minutes), and login with ' vagrant / vagrant '.
