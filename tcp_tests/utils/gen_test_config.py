#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import copy
import ConfigParser

import json

from itertools import chain
from itertools import ifilter
from collections import namedtuple
from collections import OrderedDict
from heatclient import client as heatclient
from keystoneauth1.identity import V2Password
from keystoneauth1.session import Session as KeystoneSession

SshHost = namedtuple("SshHost",
                     "roles node_name host login password keys")

# host_tmpl = {
#     "roles": ["salt_master"],
#     "node_name": "cfg01.mk22-lab-dvr.local",
#     "host": "172.16.10.100",
#     "address_pool": "admin-pool01",
#     "login": "root",
#     "password": "r00tme"}

CONFIG_TMPL = OrderedDict([
    ('hardware', {
        'env_manager': 'heat',
        'current_snapshot': None
    }),
    ('underlay', {
        'ssh': None,
        'roles': None,
    }),
    ('salt', {
        'salt_master_host': None
    })
])


def fill_hosts(hosts, ssh_key=None):
    ret = []
    for h in hosts:

        ret.append(
            SshHost(
                roles=h['roles'],
                node_name=h['hostname'],
                host=h['public_ip'],
                login='ubuntu',
                password='ubuntu',
                keys=[ssh_key] if ssh_key else []))
    return ret


def get_heat():
    keystone_auth = V2Password(
        auth_url=os.environ['OS_AUTH_URL'],
        username=os.environ['OS_USERNAME'],
        password=os.environ['OS_PASSWORD'],
        tenant_name=os.environ['OS_TENANT_NAME'])
    session = KeystoneSession(auth=keystone_auth, verify=False)
    endpoint_url = session.get_endpoint(
        service_type='orchestration',
        endpoint_type='publicURL')
    heat = heatclient.Client(
        version='1',
        endpoint=endpoint_url,
        token=session.get_token())
    return heat


def fill_config(hosts, env_name, last_snapshot):
    ini = copy.deepcopy(CONFIG_TMPL)

    ini['hardware']['current_snapshot'] = last_snapshot
    ini['underlay']['ssh'] = json.dumps([h.__dict__ for h in hosts])
    ini['underlay']['roles'] = json.dumps(
        list(set(chain(*[h.roles for h in hosts]))))
    ini['salt']['salt_master_host'] = next(h.host for h in hosts
                                           if 'salt-master' in h.roles)

    return ini


def save_ini_config(ini, filename):
    config = ConfigParser.ConfigParser()

    for s in ini:
        config.add_section(s)
        for k, v in ini[s].items():
            config.set(s, k, v)

    with open(filename, 'w') as f:
        config.write(f)


def print_help():
    text = """
    Usage: {command} HEAT_STACK_NAME HEAT_SNAPHOT_NAME
    """.format(command=sys.argv[0])
    print(text)
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print_help()

    heat = get_heat()
    env_name = sys.argv[1]
    snapshot = sys.argv[2]
    ssh_key = next(iter(sys.argv[3:]), None)
    stack = heat.stacks.get(env_name)
    hosts = next(ifilter(
        lambda v: v['output_key'] == 'hosts', stack.outputs))['output_value']
    hosts = list(chain(*hosts))
    hosts = fill_hosts(hosts, ssh_key=ssh_key)
    ini = fill_config(hosts, env_name, snapshot)
    save_ini_config(ini, "{name}_{snapshot}.ini".format(name=env_name,
                                                        snapshot=snapshot))


if __name__ == '__main__':
    main()
