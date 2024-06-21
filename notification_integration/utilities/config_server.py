# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
from typing import Any, Dict
from google.cloud import storage


class Error(Exception):
  """Base error for this module."""

  pass


class ConfigServerInitError(Error):
  """Exception raised when failed to initialize the config server."""

  pass


class InvalidConfigDataError(Error):
  """Config data is invalid."""

  pass


class ConfigNotFoundError(Error):
  """A config is not found."""

  pass


class ParamNotFoundError(Error):
  """A config parameter is not found."""

  pass


# Private helper functions.
def _GetConfigFromConfigMap(
    config_id: str, config_map: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
  """Retrieves the configuration based on the config ID."""
  try:
    return config_map[config_id]
  except BaseException as e:
    err_msg = f'Failed to get the configuration parameter {config_id}: {e}'
    raise ConfigNotFoundError(err_msg) from e


def _GetConfigParamFromConfigMap(
    config_id: str, param_name: str, config_map: Dict[str, Dict[str, Any]]
) -> Any:
  """Retrieves the configuration parameter based on the config ID and parameter name."""
  config = _GetConfigFromConfigMap(config_id, config_map)
  try:
    return config[param_name]
  except BaseException as e:
    err_msg = (
        'Failed to get the configuration parameter'
        f' {config_id}/{param_name}: {e}'
    )
    raise ParamNotFoundError(err_msg) from e


def _ValidateConfigMap(config_map: Any):
  """Raises exception if the config map is not a valid Dict[str, Dict[str, Any]] object."""
  if not isinstance(config_map, dict):
    raise InvalidConfigDataError('The configuration is not a dict json object')

  for k, v in config_map.items():
    if not (isinstance(k, str) and isinstance(v, dict)):
      raise InvalidConfigDataError(
          'The configuration map must be a Dict[str, Dict[str, Any]] object.'
      )
    for config_k, _ in v.items():
      if not isinstance(config_k, str):
        raise InvalidConfigDataError(
            'The configuration map must be a  Dict[str, Dict[str, Any]] object.'
        )


class ConfigServer(abc.ABC):
  """Abstract base class that represents a configuration server."""

  @abc.abstractmethod
  def GetConfig(self, config_id: str) -> Dict[str, Any]:
    """Retrieves the config parameters from a given configuration.

    Args:
       config_id: The id of the configuration to retrieve.

    Returns:
        The corresponding config parameters.

    Raises:
        Any exception raised when retrieving the config parameters.
    """
    pass

  @abc.abstractmethod
  def GetConfigParam(self, config_id: str, param_name: str) -> Any:
    """Retrieves the config parameters from a given configuration.

    Args:
       config_id: The id of the configuration to retrieve.
       param_name: The name of the parameter to retrieve.

    Returns:
        The corresponding config parameters.

    Raises:
        Any exception raised when retrieving the config parameters.
    """
    pass


class InMemoryConfigServer(ConfigServer):
  """A simple config server that uses a in-memory dict to save the config data.

  The configuration data is a dictory that  maps the config id into a
  configuration.
  The configuration object is also  a dictionary that maps parameter names into
  the values.
  """

  def __init__(self, config_map: Dict[str, Dict[str, Any]]):
    _ValidateConfigMap(config_map)
    self._config_map = config_map

  def GetConfig(self, config_id: str) -> Dict[str, Any]:
    """Retrieves the configuration."""
    return _GetConfigFromConfigMap(config_id, self._config_map)

  def GetConfigParam(self, config_id: str, param_name: str) -> Any:
    """Retrieves the configuration parameter."""
    return _GetConfigParamFromConfigMap(config_id, param_name, self._config_map)


class GcsConfigServer(ConfigServer):
  """Google storage (GCS) based configuration server.

  The configuration is saved as a GCS object (file). It is a file that includes
  a json object. The json object is a dictory that maps the config id into a
  configuration. The configuration object is also a dictionary that maps
  parameter names into the values.

  To use this configuration server, make sure the Cloud Run service account (the
  default one is
  PROJECT_NUMBER-compute@developer.gserviceaccount.com) has permission to read
  the GCS object.
  """

  def __init__(self, bucket_name: str, file_name: str):
    try:
      storage_client = storage.Client()
      bucket = storage_client.get_bucket(bucket_name)
    except BaseException as e:
      err_msg = 'Failed to get the GCS bucket {bucket_name}: {e}'.format(
          bucket_name=bucket_name, e=e
      )
      raise ConfigServerInitError(err_msg) from e

    try:
      blob = bucket.get_blob(file_name)
    except BaseException as e:
      err_msg = (
          'Failed to get the GCS object {bucket_name}/{file_name} {e}'.format(
              bucket_name=bucket_name, file_name=file_name, e=e
          )
      )
      raise ConfigServerInitError(err_msg) from e

    try:
      raw_content = blob.download_as_string()
      config_map = json.loads(raw_content)
    except BaseException as e:
      err_msg = (
          'Failed to load the configuration map from the GCS '
          'object {bucket_name}/{file_name} {e}'
      ).format(bucket_name=bucket_name, file_name=file_name, e=e)
      raise ConfigServerInitError(err_msg) from e

    _ValidateConfigMap(config_map)
    self._in_memory_server = InMemoryConfigServer(config_map)

    logging.info(
        'Successfully loaded the config data from %s/%s',
        bucket_name,
        file_name,
    )

  def GetConfig(self, config_id: str) -> Dict[str, Any]:
    """Retrieves the configuration."""
    return self._in_memory_server.GetConfig(config_id)

  def GetConfigParam(self, config_id: str, param_name: str) -> Any:
    """Retrieves the configuration parameter."""
    return self._in_memory_server.GetConfigParam(config_id, param_name)
