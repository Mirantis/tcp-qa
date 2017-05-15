#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import copy
import os
import time

import pytest

from tcp_tests import settings
from tcp_tests.helpers import ext
from tcp_tests import logger

LOG = logger.logger


class TestIronicStandalone(object):
    """Test class for testing TCP deployment"""

    @pytest.mark.fail_snapshot
    def test_install_ironic_standalone(self, config, underlay):
        """Install a VM with standalone ironic

        Before using, please set the correct roles and timeout:

            export ROLES=["ironic_master",]
            export BOOTSTRAP_TIMEOUT=900

        , and unset these variables after the bootstrap is completed.

        Scenario:
            1. Install Ironic service and helper services
            2. Build ironic agent image
            3. Download Ubuntu cloud image and calculate MD5
            4. export environment variables to further use

        """
        cmd = "md5sum /httpboot/xenial-server-cloudimg-amd64.qcow2 | awk '{print $1}'"
        res = underlay.check_call(cmd, host=config.salt.salt_master_host, verbose=True)

        ironic_url = 'http://{0}:6385/'.format(config.salt.salt_master_host)
        os.environ['CLOUDINIT_IMAGE_MD5'] = res['stdout']
        os.environ['OS_AUTH_TOKEN'] = 'fake-token'
        os.environ['IRONIC_URL'] = ironic_url

        LOG.info("Ironic standalone server installed, to use it:\n"
                 "    export OS_AUTH_TOKEN=fake-token\n"
                 "    export IRONIC_URL={0}\n"
                 "    export CLOUDINIT_IMAGE_MD5={1}"
                 .format(ironic_url, res['stdout']))
