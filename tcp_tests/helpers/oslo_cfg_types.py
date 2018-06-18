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
import json
import os

from oslo_config import cfg
from oslo_config import types


# See http://docs.openstack.org/developer/oslo.config/types.html
Boolean = types.Boolean
Integer = types.Integer
Float = types.Float
String = types.String
MultiString = types.MultiString
List = types.List
Dict = types.Dict
IPAddress = types.IPAddress
Hostname = types.Hostname
URI = types.URI


# JSON config types inspired by https://review.openstack.org/100521
class JSONList(types.ConfigType):
    """JSON list type.

       Decode JSON list from a string value to python list.
    """

    def __init__(self, type_name='JSONList value'):
        super(JSONList, self).__init__(type_name=type_name)

    def __call__(self, value):
        if isinstance(value, list):
            return value

        try:
            result = json.loads(value)
        except ValueError:
            raise ValueError("No JSON object could be decoded from the value: "
                             "{0}".format(value))
        if not isinstance(result, list):
            raise ValueError("Expected JSONList, but decoded '{0}' from the "
                             "value: {1}".format(type(result), value))
        return result

    def __repr__(self):
        return 'JSONList'

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def _formatter(self, value):
        return json.dumps(value)


class JSONDict(types.ConfigType):
    """JSON dictionary type.

       Decode JSON dictionary from a string value to python dict.
    """
    def __init__(self, type_name='JSONDict value'):
        super(JSONDict, self).__init__(type_name=type_name)

    def __call__(self, value):
        if isinstance(value, dict):
            return value

        try:
            result = json.loads(value)
        except ValueError:
            raise ValueError("No JSON object could be decoded from the value: "
                             "{0}".format(value))
        if not isinstance(result, dict):
            raise ValueError("Expected JSONDict, but decoded '{0}' from the "
                             "value: {1}".format(type(result), value))
        return result

    def __repr__(self):
        return 'JSONDict'

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def _formatter(self, value):
        return json.dumps(value)


class Cfg(cfg.Opt):
    """Wrapper for cfg.Opt class that reads default form evironment variables.
    """
    def __init__(self, *args, **kwargs):

        # if 'default' in kwargs:
        #    # Load a default environment variable with expected type
        #    kwargs['default'] = args[1](
        #        os.environ.get(env_var_name, kwargs.get('default', None))
        #    )

        env_var_name = args[0].upper()
        if env_var_name not in os.environ:
            env_var_name = args[0]
        if env_var_name in os.environ:
            # args[1] is 'type' class for the current value
            self.environment_value = args[1](os.environ.get(env_var_name))
            default = kwargs.get('default', '')
            kwargs['default'] = args[1](self.environment_value)
            print('{0}={1} (default = {2}) # {3}'
                  .format(env_var_name,
                          self.environment_value,
                          default,
                          kwargs.get('help', '')))

        super(Cfg, self).__init__(*args, **kwargs)

        # Print info about default environment variables to console
        # print('{}={} (default)  # {}'.format(env_var_name,
        #                                     kwargs.get('default', ''),
        #                                     kwargs.get('help', '')))

    def _get_from_namespace(self, namespace, group_name):
        res = super(Cfg, self)._get_from_namespace(namespace, group_name)
        # Use the value from enviroment variable instead of config
        if hasattr(self, 'environment_value'):
            res = (self.environment_value, res[1])
        return res
