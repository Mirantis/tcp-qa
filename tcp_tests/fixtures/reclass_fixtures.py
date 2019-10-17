import pytest

from tcp_tests import logger
from tcp_tests.managers import reclass_manager

LOG = logger.logger


@pytest.fixture(scope='session')
def reclass_actions(config, underlay_actions):
    """Fixture that provides various actions for salt

    :param config: fixture provides oslo.config
    :param underlay_actions: fixture provides underlay manager
    :rtype: ReclassManager
    """
    return reclass_manager.ReclassManager(config, underlay_actions)
