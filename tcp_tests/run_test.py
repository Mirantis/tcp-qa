#!/usr/bin/env python

import os
import sys

import pytest

import tcp_tests


def shell():
    if len(sys.argv) > 1:
        # Run py.test for tcp_tests module folder with specified options
        testpaths = os.path.dirname(tcp_tests.__file__)
        opts = ' '.join(sys.argv[1:])
        addopts = '-vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml'
        return pytest.main('{testpaths} {addopts} {opts}'.format(
            testpaths=testpaths, addopts=addopts, opts=opts))
    else:
        return pytest.main('--help')


if __name__ == '__main__':
    sys.exit(shell())
