#!/usr/bin/env python

"""
A wrapper to ``pepper``, a CLI interface to a remote salt-api instance.

Return a single parameter from the salt model for specified
target and pillar.

Fails if the result contains more than one parameter.

Use the pepper CLI parameters to set salt-api access parameters
or set the environment variables:

  export SALTAPI_URL=http://${SALT_MASTER_IP}:6969/;
  export SALTAPI_USER='salt';
  export SALTAPI_PASS='pass';
  export SALTAPI_EAUTH='pam';
"""
from __future__ import print_function

import sys
import json

from pepper import cli


runner = cli.PepperCli()
runner.parser.description = __doc__


if len(sys.argv) <= 1:
    sys.argv.append('--help')

results = []
for res in runner.run():
    results.append(res)

if not results:
    print("Empty response", file=sys.stderr)
    sys.exit(1)

if len(results) > 1:
    print("Too many results", file=sys.stderr)
    sys.exit(1)

if results[0][0] != 0:
    print("Error code returned", file=sys.stderr)
    sys.exit(results[0][0])

data = json.loads(results[0][1])
nodes = data['return'][0].keys()

if not nodes:
    print("Wrong target: no minions selected", file=sys.stderr)
    sys.exit(1)

if len(nodes) > 1:
    print("Wrong target: too many minions selected: {0}"
          .format(nodes), file=sys.stderr)
    sys.exit(1)

print(data['return'][0][nodes[0]])
