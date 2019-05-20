#!/bin/bash -xe

apt-get update

# for Jenkins agent
apt-get install -y openjdk-8-jre-headless
# for fuel-devops and tcp-qa
apt-get install -y libyaml-dev libffi-dev libvirt-dev python-dev pkg-config vlan bridge-utils python-pip python3-pip virtualenv
# additional tools
apt-get install -y ebtables curl ethtool iputils-ping lsof strace tcpdump traceroute wget iptables htop \
    git jq ntpdate tree mc byobu at pm-utils genisoimage iotop

# ldap
apt-get install -y ldap-auth-client nscd ldap-utils

# update kernel
apt-get install -y linux-generic-hwe-16.04
