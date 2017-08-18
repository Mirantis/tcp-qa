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

[1] https://github.com/dis-xcom/reclass_tools