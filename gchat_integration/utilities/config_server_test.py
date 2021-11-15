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

# Source code from https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/run/pubsub/main_test.py
"""Unit tests for config_server.py under utilities/"""
import unittest
from unittest.mock import Mock
from google.cloud import storage
from utilities import config_server

class ConfigServerTest(unittest.TestCase):
    def testAbstactConfigServerCanNotBeInitialized(self):
        with self.assertRaises(TypeError):
            config_server.ConfigServer()  # pylint: disable=abstract-class-instantiated 


class GcsConfigServerTest(unittest.TestCase):
    def setUp(self):
        # To mock the GCS blob returned by bucket.get_blob.
        self._blob_mock = Mock()

        # To mock the GCS bucket returned by storage_client.get_bucket.
        self._bucket_mock = Mock()
        self._bucket_mock.get_blob_mock = Mock(return_value=self._bucket_mock)

        # To mock storage_client.
        self._storage_client_mock =  Mock()
        self._storage_client_mock.get_bucket = Mock(return_value=self._bucket_mock)

        storage.Client = Mock(return_value=self._storage_client_mock)

        # Dummy GCS bucket name and GCS object name used in the tests. 
        self._test_bucket = 'test_bucket'
        self._test_filename = 'test_file'

    def testInitFailedDueToGetBucketException(self):
        error_msg = 'Bucket not found'
        self._storage_client_mock.get_bucket.side_effect = ValueError(error_msg)
        with self.assertRaisesRegex(config_server.ConfigServerInitError, f'{error_msg}'):
            config_server.GcsConfigServer(self._test_bucket, self._test_filename)
        storage.Client.assert_called_once()
        self._storage_client_mock.get_bucket.assert_called_once_with(self._test_bucket)    

    def testInitFailedDueToGetBlobException(self):
        error_msg = 'Object not found'
        self._bucket_mock.get_blob.side_effect = ValueError(error_msg)

        with self.assertRaisesRegex(config_server.ConfigServerInitError, f'{error_msg}'):
            config_server.GcsConfigServer(self._test_bucket, self._test_filename)
        self._bucket_mock.get_blob.assert_called_once_with(self._test_filename)    


if __name__ == '__main__':
    unittest.main()
