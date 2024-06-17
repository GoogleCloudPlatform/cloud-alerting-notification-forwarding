# Copyright 2021 Google LLC.
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
"""Unit tests for config_server.py."""
import json
import unittest
from google.cloud import storage
from utilities import config_server

# A valid config map used in the tests.
_VALID_CONFIG_MAP = {
    'channel-1': {'service_name': 'chat', 'webhook_url': 'https://chat.123.com'}
}
_VALID_CONFIG_MAP_JSON_STR = json.dumps(_VALID_CONFIG_MAP)


class ConfigServerTest(unittest.TestCase):

  def testAbstactConfigServerCanNotBeInitialized(self):
    with self.assertRaises(TypeError):
      config_server.ConfigServer()  # pylint: disable=abstract-class-instantiated


class InMemoryConfigServerTest(unittest.TestCase):

  def setUp(self):
    # Call to the parent class's setUp method
    super().setUp()
    self._test_server = config_server.InMemoryConfigServer(_VALID_CONFIG_MAP)

  def testInitFailedDueToBadConfigMap(self):
    invalid_config_maps = [
        {123: 'test'},  # Key is not a string
        {'123': '456'},  # Value is not a dict.
        {'123': {123: 456}},  # Value is not a Dict[Text, Any]
    ]
    for config_map in invalid_config_maps:
      with self.assertRaises(config_server.InvalidConfigData):
        config_server.InMemoryConfigServer(config_map)

  def testGetConfigInvaidConfigId(self):
    with self.assertRaises(config_server.ConfigNotFoundError):
      self._test_server.GetConfig('channel-2')

  def testGetConfigSucceed(self):
    returned_val = self._test_server.GetConfig('channel-1')
    expected_val = {
        'service_name': 'chat',
        'webhook_url': 'https://chat.123.com',
    }
    self.assertDictEqual(returned_val, expected_val)

  def testGetConfigParamInvaidParamName(self):
    with self.assertRaises(config_server.ParamNotFoundError):
      self._test_server.GetConfigParam('channel-1', 'type')

  def testGetConfigParamSucceed(self):
    returned_val = self._test_server.GetConfigParam('channel-1', 'webhook_url')
    expected_val = 'https://chat.123.com'
    self.assertEqual(returned_val, expected_val)


class GcsConfigServerTest(unittest.TestCase):

  def setUp(self):
    # Call to the parent class's setUp method
    super().setUp()

    # To mock the GCS blob returned by bucket.get_blob.
    self._blob_mock = unittest.Mock()

    # To mock the GCS bucket returned by storage_client.get_bucket.
    self._bucket_mock = unittest.Mock()
    self._bucket_mock.get_blob = unittest.Mock(return_value=self._blob_mock)

    # To mock storage_client.
    self._storage_client_mock = unittest.Mock()
    self._storage_client_mock.get_bucket = unittest.Mock(
        return_value=self._bucket_mock
    )

    storage.Client = unittest.Mock(return_value=self._storage_client_mock)

    # Dummy GCS bucket name and GCS object name used in the tests.
    self._test_bucket = 'test_bucket'
    self._test_filename = 'test_file'

    # Create a test server and reset all the call
    # attributes on the mock objects.
    self._blob_mock.download_as_string.return_value = _VALID_CONFIG_MAP_JSON_STR
    self._test_server = config_server.GcsConfigServer(
        self._test_bucket, self._test_filename
    )
    self._blob_mock.reset_mock()
    self._bucket_mock.reset_mock()
    self._storage_client_mock.reset_mock()
    storage.Client.reset_mock()

  def testInitFailedDueToGetBucketException(self):
    error_msg = 'Bucket not found'
    self._storage_client_mock.get_bucket.side_effect = ValueError(error_msg)
    with self.assertRaisesRegex(
        config_server.ConfigServerInitError, f'{error_msg}'
    ):
      config_server.GcsConfigServer(self._test_bucket, self._test_filename)
    storage.Client.assert_called_once()
    self._storage_client_mock.get_bucket.assert_called_once_with(
        self._test_bucket
    )

  def testInitFailedDueToGetBlobException(self):
    error_msg = 'Object not found'
    self._bucket_mock.get_blob.side_effect = ValueError(error_msg)

    with self.assertRaisesRegex(
        config_server.ConfigServerInitError, f'{error_msg}'
    ):
      config_server.GcsConfigServer(self._test_bucket, self._test_filename)
    self._bucket_mock.get_blob.assert_called_once_with(self._test_filename)

  def testInitFailedDueToBlobDownlaodException(self):
    error_msg = 'Blob download failed'
    self._blob_mock.download_as_string.side_effect = ValueError(error_msg)

    with self.assertRaisesRegex(
        config_server.ConfigServerInitError, f'{error_msg}'
    ):
      config_server.GcsConfigServer(self._test_bucket, self._test_filename)
    self._blob_mock.download_as_string.assert_called_once_with()

  def testInitFailedDueToBlobJsonLoadsFailed(self):
    self._blob_mock.download_as_string.return_value = '{:::}'

    with self.assertRaises(config_server.ConfigServerInitError):
      config_server.GcsConfigServer(self._test_bucket, self._test_filename)
    self._blob_mock.download_as_string.assert_called_once_with()

  def testInitFailedDueToBlobInvaidContent(self):
    invalid_blob_json_strs = [
        '123',  # Not a dict.
        '{"name-1": ["webhook_url", "https://123"]}',  # Not a dict value.
        '{"1": "2"}',  # Not a dict value.
    ]
    for json_str in invalid_blob_json_strs:
      self._blob_mock.download_as_string.return_value = json_str
      with self.assertRaises(config_server.InvalidConfigData):
        config_server.GcsConfigServer(self._test_bucket, self._test_filename)

  def testGetConfigInvaidConfigId(self):
    with self.assertRaises(config_server.ConfigNotFoundError):
      self._test_server.GetConfig('channel-2')

  def testGetConfigSucceed(self):
    returned_val = self._test_server.GetConfig('channel-1')
    expected_val = {
        'service_name': 'chat',
        'webhook_url': 'https://chat.123.com',
    }
    self.assertDictEqual(returned_val, expected_val)

  def testGetConfigParamInvaidParamName(self):
    with self.assertRaises(config_server.ParamNotFoundError):
      self._test_server.GetConfigParam('channel-1', 'type')

  def testGetConfigParamSucceed(self):
    returned_val = self._test_server.GetConfigParam('channel-1', 'webhook_url')
    expected_val = 'https://chat.123.com'
    self.assertEqual(returned_val, expected_val)


if __name__ == '__main__':
  unittest.main()
