Template for deploying mitaka models with trusty:
- virtual-mcp-mitaka-dvr-trusty
- virtual-mcp-mitaka-ovs-trusty

Used by maintenance team.

Use following env vars should be used:
SALT_MODELS_COMMIT = 'fa85f84'
SALT_MODELS_SYSTEM_TAG = '2018.8.0'
REPOSITORY_SUITE = '2018.8.0'
OVERRIDES = 'openstack_log_appender: true
linux_system_repo_mk_openstack_version: testing
'

Also VCP 2018.8.0 images should be used