# tcp-qa

Default template used here requires 20 vCPU and 52Gb host RAM.

Clone the repo
--------------
```
git clone https://github.com/Mirantis/tcp-qa
cd ./tcp-qa
```

Install requirements
--------------------
```
pip install -r ./tcp_tests/requirements.txt
```
* Note: Please read [1] if you don't have fuel-devops installed, because there are required some additional packages and configuration.

Get cloudinit image
-------------------
```
wget https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img -O ./xenial-server-cloudimg-amd64.qcow2
```

Choose the name of the cluster model
------------------------------------
LAB_CONFIG_NAME variable maps cluster name from the model repository with
the set of templates in the ./tcp_tests/templates/ folder.
```
export LAB_CONFIG_NAME=virtual-mcp-ocata-dvr  # OVS-DVR with ocata packages
export LAB_CONFIG_NAME=virtual-mcp-ocata-ovs  # OVS-NO-DVR with ocata packages
export LAB_CONFIG_NAME=virtual-mcp11-dvr  # OVS-DVR with neutron packages
export LAB_CONFIG_NAME=virtual-mcp11-ovs  # OVS-NO-DVR with neutron packages
export LAB_CONFIG_NAME=virtual-mcp11-dpdk  # OVS-DPDK with neutron packages
```

Run deploy test
---------------
```
export IMAGE_PATH1604=./xenial-server-cloudimg-amd64.qcow2
export SHUTDOWN_ENV_ON_TEARDOWN=false  # Optional

LC_ALL=en_US.UTF-8  py.test -vvv -s -k test_tcp_install_default
```

Run deploy test and rally verify (tempest)
------------------------------------------
```
export IMAGE_PATH1604=./xenial-server-cloudimg-amd64.qcow2
export SHUTDOWN_ENV_ON_TEARDOWN=false  # Optional

LC_ALL=en_US.UTF-8  py.test -vvv -s -k test_tcp_install_run_rally
```

Run deploy test for mk22-qa-lab01 (outdated)
--------------------------------------------
Note: This lab is not finished yet. TBD: configure vsrx node
```
export ENV_NAME=tcpcloud-mk22  # You can set any env name
export LAB_CONFIG_NAME=mk22-qa-lab01  # Name of set of templates
export VSRX_PATH=./vSRX.img           # /path/to/vSRX.img, or to ./xenial-server-cloudimg-amd64.qcow2 as a temporary workaround

LC_ALL=en_US.UTF-8  py.test -vvv -s -k test_tcp_install_default
```
, or as an alternative there is another test that use deploy scripts from models repository written on bash [2]:
```
LC_ALL=en_US.UTF-8  py.test -vvv -s -k test_tcp_install_with_scripts
```

Labs with names mk22-lab-basic and mk22-lab-avdanced are deprecated and not recommended to use.


Create and start the env for manual tests
-----------------------------------------
```
dos.py create-env ./tcp_tests/templates/underlay/mk22-lab-basic.yaml
dos.py start "${ENV_NAME}"
```

Then, wait until cloud-init is finished and port 22 is open (~3-4 minutes), and login with root:r00tme

[1] https://github.com/openstack/fuel-devops/blob/master/doc/source/install.rst

[2] https://github.com/Mirantis/mk-lab-salt-model/tree/dash/scripts
