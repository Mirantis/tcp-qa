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
import yaml

from pepper import cli


if len(sys.argv) <= 1:
    sys.argv.append('--help')

# Use async request with checking for failed minions
sys.argv.append("--fail-if-incomplete")

tries = 3
for _ in range(tries):
    results = []

    runner = cli.PepperCli()
    runner.parser.description = __doc__

    for res in runner.run():
        results.append(res)
    if results and len(results) > 1:
        break

# Expected: list of two touples:
# - first touple should contain the result in string format (pepper issue)
# - second touple should contain failed nodes
# Example:
#   [(None, '"{cid01.cookied-cicd-queens-dvr-sl.local: "some data"}"'),
#    (0, '"{Failed: []}"')]
# Example when node is not responding:
#   [(1, '"{Failed: [u\'cid01.cookied-cicd-queens-dvr-sl.local\']}"')]

if not results or len(results) < 2:
    print("Empty response", file=sys.stderr)
    sys.exit(1)

if len(results) > 2:
    print("Too many results", file=sys.stderr)
    sys.exit(1)

if results[-1][0] != 0:
    print("Error code returned", file=sys.stderr)
    sys.exit(results[0][0])

data = yaml.load(json.loads(results[0][1]))
nodes = data.keys()

if not nodes:
    print("Wrong target: no minions selected", file=sys.stderr)
    sys.exit(1)

if len(nodes) > 1:
    print("Wrong target: too many minions selected: {0}"
          .format(nodes), file=sys.stderr)
    sys.exit(1)

print(data[nodes[0]])
