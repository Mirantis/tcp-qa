Render the template
-------------------

Use reclass_tools from [1] to render the template.

<env_name> : any name for newly created environment model
<path_to_template> : path to the directory with the cookiecutter template, for example 'tcp-qa/tcp_tests/environment/environment_template'
<destination_path> : path to directory where will be created the new environment model
<inventory_fileN> : path to the YAML with the inventory data. Can be specified multiple times to use different parts of the inventory. VCP inventory must be specified for current workflow (when all linux.network.interface are deleted)


```
reclass-tools render -e <env_name> -t <path_to_template> -o <destination_path> -c <inventory_file1> -c <inventory_file2> [...] -c <inventory_fileN>
```

To attach the environment model to any cluster, use the instructions from [1]

[1] https://github.com/dis-xcom/reclass_tools


Template architecture
---------------------

```
└── environment_template
    ├── {{ cookiecutter._env_name }}
    │   ├── init.yml
    │   ├── linux_network_interface.yml
    │   ├── linux_system_codename_trusty.yml
    │   ├── linux_system_codename_xenial.yml
    │   ├── {# interfaces #} -> ../{# interfaces #}
    │   └── {# roles #} -> ../{# roles #}
    ├── {# interfaces #}
    │   └── ...
    └── {# roles #}
        └── ...
```

* {{ cookiecutter._env_name }} : folder that will be used to generate the new Environment model, contains:

  - init.yml : file that will be filled with reclass:storage:node pillars generated using inventory files. This is the main file that must be
               included to cfg01.* node before generating the reclass inventory with the salt state 'reclass.storage'.

  - linux_network_interface.yml : it is a workaround to make possible to pass the linux:network:interface configuration separatelly for each node.
                                  This is because reclass.storage state works only with parameters:_param:* pillars and cannot be used
                                  to add any other pillar data to parameters:* (for example, parameters:linux:network:interface).
                                  So, linux network interface configuration is stored in the intermediate variable parameters:_param:linux_network_interfaces
                                  for each node, and then included to the parameters:linux:network:interface using this file as a class attached
                                  to each node by default.
  - linux_system_codename_*.yml : A class with a single variable. Allows to specify the specific linux version using only node role.

  - {# interfaces #} : symlink to the {# interfaces #} folder outside of the cookiecutter template directory, to not pass it's content to the
                       resulting model during the model rendering.

  - {# roles #} : symlink to the {# roles #} folder outside of the cookiecutter template directory, to not pass it's content to the
                  resulting model during the model rendering.

* {# interfaces #} : Interface role means the name of the file that will be included and rendered.
                     Contains *text* patterns of YAML file that are included to the init.yml under linux_network_interface: parameters
                     using Jinja.
                     Each pattern provides the mapping of the physical interfaces which have the same role on some logical networking objects
                     (OVS, bonds, bridges, ...). These networking objects provide the Underlay interfaces used for upcoming cluster architecture.

* {# roles #} : Node roles mean the name of the files that will be included and rendered under the 'classes:' object.
                Contains *text* patterns of YAML file that are included to the init.yml and must provide only the
                list of the classes for the specific node.

In the init.yml is defined a dict variable 'params' that is accessible from files in {# interfaces #} and {# roles #}.
'params' may be used by Jinja expressions in these folders to generate some additional dynamic 'parameters:_param' pillars that cannot be specified
as a fixed value in a class.

If you need to specify a fixed values, please do the following:
- add a new class file *.yml file next to the init.yml with the necessary *FIXED* parameters (example: linux_system_codename_xenial.yml)
- add a node role to the {# roles #} directory that will include your environment.{{ cookiecutter._env_name }}.<class file from first step>
- use the created node role in the inventory for required nodes


Inventory examples
------------------

Inventory must include all the nodes, physical or virtual.
'reclass_storage_name' is used for back compatibility until some parameters
are still inherited from the cluster/system level of the reclass:storage pillars.

Physical node example:
```
nodes:
    kvm01.mcp11-ovs-dpdk.local:
      reclass_storage_name: infra_kvm_node01
      roles:
      - infra_kvm
      - linux_system_codename_xenial
      interfaces:
        enp3s0f0:
          role: single_mgm
        enp3s0f1:
          role: bond0_ab_nondvr_vxlan_ctl_mesh
```

Virtual Control Plane node example:
```
nodes:
    ctl01.mcp11-ovs-dpdk.local:
      reclass_storage_name: openstack_control_node01
      roles:
      - openstack_control_leader
      - linux_system_codename_xenial
      interfaces:
        ens3:
          role: single_ctl
```
