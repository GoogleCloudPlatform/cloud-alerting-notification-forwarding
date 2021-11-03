# Copyright 2021 Google, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration servers that provide 3rd-party integration parameters."""

import abc
import json
import logging
from typing import Any, Text
from google.cloud import storage

class Error(Exception):
    """Base error for this module."""
    pass

class ConfigServerInitError(Error):
    """Exception raised when failed to initialize the config server."""
    pass

class InvalidConfigData(Error):
    """Config data is invalid."""
    pass

class ParamNotFoundError(Error):
    """Config parameter is not found."""
    pass

class ConfigServer(abc.ABC):
    """Abstract base class that represents a configuration server."""

    @abc.abstractmethod
    def GetConfigParam(self, config_id: Text, param_name: Text) -> Any:
        """Retrieves a parameter from a given configuration.
        Args:
           config_id: The id of the configuration to retrieve.
           param_name: The name of the parame to retrieve.

        Returns:
            The corresponding parameter value.
       
        Raises:
            Any exception raised when retrieving the param. value.  
        """
        pass

class GcsConfigServer(ConfigServer):
    """Google storage (GCS) based configuration server.
    
    The configuration is saved as a GCS object (file). It is a file that includes a json object. The json
    object is a dictory that maps the config id into a configuration. The configuration object is also 
    a dictionary that maps parameter names into their values.

    To use this configuration server, make sure the Cloud Run service account (the default one is PROJECT_NUMBER-compute@developer.gserviceaccount.com) has permission to read the GCS object.
    """
    def __init__(self, bucket_name: Text, file_name: Text):
        try:
            storage_client = storage.Client()
            bucket = storage_client.get_bucket(bucket_name)
        except BaseException as e:
            err_msg = 'Failed to get the GCS bucket {bucket_name}: {e}'.format(
                bucket_name=bucket_name, e=e)
            raise ConfigServerInitError(err_msg)

        try:
            blob = bucket.get_blob(file_name)
        except BaseException as e:
            err_msg = 'Failed to get the GCS object {bucket_name}/{file_name} {e}'.format(
                bucket_name=bucket_name, file_name=file_name, e=e)
            raise ConfigServerInitError(err_msg)

        try:
            raw_content = blob.download_as_string()
            self._config_map = json.loads(raw_content)
        except BaseException as e:
            err_msg = ('Failed to load the configuration map from the GCS '
                       'object {bucket_name}/{file_name} {e}').format(
                           bucket_name=bucket_name, file_name=file_name, e=e)
            raise ConfigServerInitError(err_msg)

        if not isinstance(self._config_map, dict):
            raise InvalidConfigData('The configuration is not a dict json object')

        for k, v in self._config_map:
            if not (isinstance(k, str) and isinstance(v, dict)):
                raise InvalidConfigData('The configuration must be a Dict[str, Dict] object.')

        logging.info('Sucessfully loaded the config data from {bucket_name}/{file_name}'.format(
                bucket_name=bucket_name, file_name=file_name))

    def GetConfigParam(self, config_id: Text, param_name: Text) -> Any:
        """Retrieves a parameter from a given configuration."""
        try:
            return self._config_map[config_id][param_name]
        except BaseException as e:
            err_msg = 'Failed to get the configuration parameter {param_name}: {e}'.format(
                param_name=param_name, e=e)
            raise ParamNotFoundError(err_msg)


class HardCodedConfigServer(ConfigServer):
    """Simple hard coded config server"""
    def __init__(self)
        self._config_map = {
            

        }
        if not isinstance(self._config_map, dict):
            raise InvalidConfigData('The configuration is not a dict json object')

        for k, v in self._config_map:
            if not (isinstance(k, str) and isinstance(v, dict)):
                raise InvalidConfigData('The configuration must be a Dict[str, Dict] object.')

        logging.info('Sucessfully loaded the config data from {bucket_name}/{file_name}'.format(
                bucket_name=bucket_name, file_name=file_name))

    def GetConfigParam(self, config_id: Text, param_name: Text) -> Any:
        """Retrieves a parameter from a given configuration."""
        try:
            return self._config_map[config_id][param_name]
        except BaseException as e:
            err_msg = 'Failed to get the configuration parameter {param_name}: {e}'.format(
                param_name=param_name, e=e)
            raise ParamNotFoundError(err_msg)        