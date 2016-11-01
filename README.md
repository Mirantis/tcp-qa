# tcp-qa

Default template used here requires 20 vCPU and 52Gb host RAM.

Clone the repo
--------------

git clone https://github.com/Mirantis/tcp-qa

cd ./tcp-qa

Install requirements
--------------------

pip install -r ./tcp_tests/requirements.txt --upgrade

Initialize fuel-devops database if needed:
------------------------------------------

dos-manage.py migrate

Get cloudinit images
--------------------

wget https://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img -O ./trusty-server-cloudimg-amd64.qcow2

wget https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img -O ./xenial-server-cloudimg-amd64.qcow2

Export variables
----------------

export ENV_NAME=tcpcloud-mk22  # Optional

export IMAGE_PATH1404=./trusty-server-cloudimg-amd64.qcow2

export IMAGE_PATH1604=./xenial-server-cloudimg-amd64.qcow2

Run deploy test
---------------

export SHUTDOWN_ENV_ON_TEARDOWN=false  # Optional

py.test -vvv -s -k test_tcp_install_default


Create and start the env for manual tests
-----------------------------------------

dos.py create-env ./tcp_tests/templates/tcpcloud-default.yaml

dos.py start "${ENV_NAME}"


Then, wait until cloud-init is finished and port 22 is open (~3-4 minutes), and login with root:r00tme


Additional info
---------------

Installation steps are placed in YAML files and executed in the following order:

- Hardware (VMs) environment is created from tcp-qa/tcp_tests/templates/underlay/mk22-lab-advanced.yaml

- Salt installation and configuration steps tcp-qa/tcp_tests/templates/salt/mk22-lab-advanced-salt.yaml

- Common services installation steps tcp-qa/tcp_tests/templates/common-services/mk22-lab-advanced-common-services.yaml

- OpenStack services installation steps tcp-qa/tcp_tests/templates/openstack/mk22-lab-advanced-openstack.yaml
