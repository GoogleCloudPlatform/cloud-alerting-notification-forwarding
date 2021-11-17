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

"""Unit tests for service_handler.py."""
import json
import unittest
from httplib2 import Http
from unittest.mock import Mock
from utilities import service_handler


# A valid config map used in the tests.
_SERVICE_NAME = 'google_chat'
_HTTP_METHOD = 'POST'
_CONFIG_PARAMS = {'service_name': _SERVICE_NAME,
                  'webhook_url': 'https://chat.123.com',
                  'msg_format': 'card'
                 }


class ServiceHandlerTest(unittest.TestCase):
    def testAbstactServiceHandlerCanNotBeInitialized(self):
        with self.assertRaises(TypeError):
            service_handler.ServiceHandler(_SERVICE_NAME)  # pylint: disable=abstract-class-instantiated 


class HttpRequestBasedHandlerTest(unittest.TestCase):
    def testAbstactclassHttpRequestBasedHandlerCanNotBeInitialized(self):
        with self.assertRaises(TypeError):
            service_handler.HttpRequestBasedHandler(_SERVICE_NAME, _HTTP_METHOD)  # pylint: disable=abstract-class-instantiated 


class GchatHandlerTest(unittest.TestCase):
    def setUp(self):
        # To mock the GCS blob returned by bucket.get_blob.        
        self._http_obj_mock = Mock()
        self._http_mock = Mock(return_value=self._http_obj_mock)
        Http = self._http_mock

    def testCheckServiceNameInConfigParamsFailed(self):
        handler = service_handler.GchatHandler()
        bad_configs = [
            {'service': _SERVICE_NAME},  # Bad key
            {'service_name': 'wrong_xxx'}  # Bad value
        ]
        for bad_config in bad_configs:     
            with self.assertRaises(service_handler.ConfigParamsError):
                handler.CheckServiceNameInConfigParams(bad_config)

    def testCheckConfigParamsFailed(self):
        handler = service_handler.GchatHandler()
        bad_configs = [
            {'service': _SERVICE_NAME},  # Bad service name key
            {'service_name': 'wrong_xxx'},  # Bad service name value
            {'service_name': 'google_chat', 'url': '123.com'},  # Bad url key
            {'service_name': 'google_chat', 'webhook_url': 123},  # Bad url value
            {'service_name': 'google_chat', 'webhook_url': '123.com', 'format': 'card'},  # Bad format key
            {'service_name': 'google_chat', 'webhook_url': '123.com', 'msg_format': 'video'},  # Bad format value
        ]
        for bad_config in bad_configs:     
            with self.assertRaises(service_handler.ConfigParamsError):
                handler.CheckConfigParams(bad_config)

if __name__ == '__main__':
    unittest.main()
