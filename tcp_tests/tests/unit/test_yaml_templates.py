import pytest
import mock
import os

from tcp_tests.helpers import env_config
from tcp_tests import settings_oslo

config = settings_oslo.load_config(config_files=[])
config.underlay.ssh = [
    {"node_name": "cfg01.cookied-dop-sl2.local", "host": "10.70.0.15"},
    {"node_name": "cid01.cookied-dop-sl2.local", "host": "10.70.0.91"},
    {"node_name": "cid02.cookied-dop-sl2.local", "host": "10.70.0.92"},
    {"node_name": "cid03.cookied-dop-sl2.local", "host": "10.70.0.93"},
    {"node_name": "ctl01.cookied-dop-sl2.local", "host": "10.70.0.11"},
    {"node_name": "ctl02.cookied-dop-sl2.local", "host": "10.70.0.12"},
    {"node_name": "ctl03.cookied-dop-sl2.local", "host": "10.70.0.13"},
    {"node_name": "mon01.cookied-dop-sl2.local", "host": "10.70.0.71"},
    {"node_name": "mon02.cookied-dop-sl2.local", "host": "10.70.0.72"},
    {"node_name": "mon03.cookied-dop-sl2.local", "host": "10.70.0.73"},
    {"node_name": "prx01.cookied-dop-sl2.local", "host": "10.70.0.81"},
    {"node_name": "cmp001.cookied-dop-sl2.local", "host": "10.70.0.101"},
    {"node_name": "cmp002.cookied-dop-sl2.local", "host": "10.70.0.102"},
    {"node_name": "gtw01.cookied-dop-sl2.local", "host": "10.70.0.224"}
]

config.underlay.address_pools = {
    "admin-pool01": "10.70.0.0/24",
    "private-pool01": "10.60.0.0/24",
    "tenant-pool01": "10.80.0.0/24",
    "external-pool01": "10.90.0.0/24"
}
config.underlay.ssh_keys = [
    {"public": "AAAARRRGGHHHhh", "private": "--- BLABLA-KEY ---"}
]


def find_yaml_paths():
    exts = ['.yml', '.yaml']
    for root, subFolder, files in os.walk('./tcp_tests/templates/'):
        for filename in files:
            if any([filename.endswith(ext) for ext in exts]):
                yield str(os.path.join(root, filename))


@pytest.mark.parametrize("yaml_path", find_yaml_paths())
@pytest.mark.unit_tests
@mock.patch('os.environ', autospec=True)
def test_jinja_render_yaml_file(mock_os_environ, yaml_path):
    def os_environ_getitem(name):
        return "=< Mock value >="

    def os_environ_get(name, default_value):
        return default_value or "=< Mock value >="

    mock_os_environ.__getitem__ = mock.Mock(side_effect=os_environ_getitem)
    mock_os_environ.get = mock.Mock(side_effect=os_environ_get)

    options = {
        'config': config,
    }
    env_config.yaml_template_load(yaml_path, options=options,
                                  log_env_vars=False)
