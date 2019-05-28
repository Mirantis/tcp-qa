1. Required template parameters
===============================
Parameters with fixed names required by Jenkins pipeline swarm-bootstrap-salt-cluster-heat.groovy.
These parameters can be defined in .env or .hot file and are used to generate model.
```
management_subnet_cidr
management_subnet_gateway_ip
management_subnet_cfg01_ip
control_subnet_cidr
tenant_subnet_cidr
external_subnet_cidr
```
Also, the following parameters might be useful to define:
```
management_subnet_pool_start
management_subnet_pool_end
```

2. Required template objects
============================

2.1 Node roles
--------------

Node roles are automatically gathered in the envmanager_heat.py
from OS::Nova::Server , where defined as a list using "metadata:roles" key:

```
     cfg01_node:
       type: OS::Nova::Server
       properties:
         metadata:
           roles:
           - salt_master
```

2.2 L3 network roles
--------------------

Network roles are automatically gathered in the envmanager_heat.py
from OS::Neutron::Subnet , where defined as list of tags:

```
  control_subnet:
    type: OS::Neutron::Subnet
    properties:
      ...
      tags:
      - private-pool01
```
There are four fixed network roles at the moment:
```
admin-pool01    # for management_subnet_cidr
private-pool01  # for control_subnet_cidr
tenant-pool01   # for tenant_subnet_cidr
external-pool01 # for external_subnet_cidr
```

3. External parameters
======================

There are parameters which are automatically defined outside
of the template defaults in the envmanager_heat.py, and can be used
in the template to define or find specified resources:
```
env_name     # set from environment variable ENV_NAME. Matches heat stack name
mcp_version  # set from environment variable MCP_VERSION
```

4. Pre-defined resources in the OpenStack cloud
===============================================

4.1 Public network
------------------
Public network for floating IP addresses should be pre-defined.
Heat templates must use this network to define floating IPs.

4.2 Images
----------
Jenkins pipeline swarm-bootstrap-salt-cluster-heat.groovy check and create
required images. In the template, the following image names should be used:

```
# Image used to bootstrap salt master node cfg01:
image: { list_join: ['', [ 'cfg01-day01-', { get_param: mcp_version } ]] }

# Config drive image to boot cfg01, with user-data and reclass model
image: { list_join: ['', [ 'cfg01.', { get_param: env_name }, '-config-drive.iso' ]] }

# Image used to bootstrap VCP nodes:
image: { list_join: ['', [ 'ubuntu-vcp-', { get_param: mcp_version } ]] }

# Image used to bootstrap the Foundation node:
image: { list_join: ['', [ 'ubuntu-16.04-foundation-', { get_param: mcp_version } ]] }
```

5. The foundation node
======================
To get direct access to the environment resources without tunnels and jump hosts,
the pipeline swarm-bootstrap-salt-cluster-heat.groovy expects that a foundation node
will be defined in each heat template.

This node is used to launch a Jenkins agent and run Jenkins jobs inside the
heat stack. Depending on environment, the Foundation node could be connected
to several or to all the internal networks to run necessary tests.

The template 'outputs' should contain the 'foundation_public_ip' key, for example:
For virtual deploys:
```
outputs:
  foundation_public_ip:
    description: foundation node IP address (floating) from external network
    value:
      get_attr:
      - foundation_node
      - instance_floating_address
```
For Baremetal deploys
```
outputs:
  foundation_public_ip:
    description: foundation node IP address (floating) from external network
    value:
      get_attr:
      - foundation_node
      - instance_address # Here will get management IP
```
