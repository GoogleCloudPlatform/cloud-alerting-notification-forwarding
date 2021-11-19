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
"""Unit tests for pubsub.py"""

import base64
import binascii
import json
import unittest
from unittest.mock import Mock
from utilities import pubsub

class PubSubTest(unittest.TestCase):
    def testExtractNotificationFromPubSubMsgBadMsg(self):
        malformed_pubsub_msgs = [
            {'sent_time': '123'},  # No message field
            {'message': 'fake message'},  # No dict message
            {'message': {'date': 'Nov 18 2021'}}  # No data field in message
        ]    
        for msg in malformed_pubsub_msgs:
            with self.assertRaises(pubsub.DataParseError):
                pubsub.ExtractNotificationFromPubSubMsg(msg)      

    def testExtractNotificationFromPubSubMsgInvaidData(self):
        pubsub_msg = {'message': {'data': '~!@'}}  # 
        with self.assertRaises(pubsub.DataParseError):
            pubsub.ExtractNotificationFromPubSubMsg(pubsub_msg)      

    def testExtractNotificationFromPubSubMsgSucceed(self):
        data_str= (
            'eyJpbmNpZGVudCI6IHsicmVzb3VyY2VfaWQiOiAiIiwgInJlc291cmNlX25hb'
            'WUiOiAidGYtdGVzdCBWTSBJbnN0YW5jZSBsYWJlbHMge3Byb2plY3RfaWQ9dG'
            'YtdGVzdH0iLCAicmVzb3VyY2VfdHlwZV9kaXNwbGF5X25hbWUiOiAiVk0gSW5'
            'zdGFuY2UiLCAic3RhcnRlZF9hdCI6IDE2MjA3NTQ1MzMsICJzdGF0ZSI6ICJj'
            'bG9zZWQiLCAic3VtbWFyeSI6ICJDUFUgdXNhZ2UgZm9yIHRmLXRlc3QgVk0gS'
            'W5zdGFuY2UgbGFiZWxzIHtwcm9qZWN0X2lkPXRmLXRlc3R9IHJldHVybmVkIH'
            'RvIG5vcm1hbCB3aXRoIGEgdmFsdWUgb2YgMC4wODEuIiwgInVybCI6ICJodHR'
            'wczovL2NvbnNvbGUuY2xvdWQuZ29vZ2xlLmNvbS9tb25pdG9yaW5nL2FsZXJ0'
            'aW5nL2luY2lkZW50cy8wLm0yZDYxYjNzNmQ1ZD9wcm9qZWN0PXRmLXRlc3Qif'
            'SwgInZlcnNpb24iOiAiMS4yIn0='
        )

        pubsub_msg = {'message': {'data': data_str}}
        result = pubsub.ExtractNotificationFromPubSubMsg(pubsub_msg)
        expected_result = {
            "incident": {
                "resource_id": "",
                "resource_name": "tf-test VM Instance labels {project_id=tf-test}",
                "resource_type_display_name": "VM Instance",
                "started_at": 1620754533,
                "state": "closed",
                "summary": "CPU usage for tf-test VM Instance labels {project_id=tf-test} returned to normal with a value of 0.081.",
                "url": "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test"
            },
            "version": "1.2"
        }
        self.assertDictEqual(result, expected_result)

    def testExtractNotificationFromPubSubMsgJsonDumpsFailed(self):
        pubsub_msg = {'message': {'data': 'InsxMjM6fSI='}}  # data corresponds to '{123:}'
        #with self.assertRaises(pubsub.DataParseError):
        pubsub.ExtractNotificationFromPubSubMsg(pubsub_msg)


        