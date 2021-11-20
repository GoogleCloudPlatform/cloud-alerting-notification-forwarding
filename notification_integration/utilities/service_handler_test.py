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
import copy
import json
import httplib2
import unittest
from unittest.mock import Mock
from utilities import service_handler


# A valid config map used in the tests.
_SERVICE_NAME = 'google_chat'
_HTTP_METHOD = 'POST'
_CONFIG_PARAMS = {'service_name': _SERVICE_NAME,
                  'webhook_url': 'https://chat.123.com',
                  'msg_format': 'card'
                 }
_BAD_CONFIG_PARAMS = [
    {'service': _SERVICE_NAME},  # Bad service name key
    {'service_name': 'wrong_xxx'},  # Bad service name value
    {'service_name': 'google_chat', 'url': '123.com'},  # Bad url key
    {'service_name': 'google_chat', 'webhook_url': 123},  # Bad url value
    {'service_name': 'google_chat', 'webhook_url': '123.com', 'format': 'card'},  # Bad format key
    {'service_name': 'google_chat', 'webhook_url': '123.com', 'msg_format': 'video'},  # Bad format value
]

# Test notification json object.
_NOTIF = {
    "incident": {
        "condition": {
            "conditionThreshold": {
                "aggregations": [
                    {
                        "alignmentPeriod": "60s",
                        "crossSeriesReducer": "REDUCE_SUM",
                        "perSeriesAligner": "ALIGN_SUM"
                    }
                ],
                "comparison": "COMPARISON_GT",
                "duration": "60s",
                "filter": "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" AND resource.type=\"gce_instance\"",
                "trigger": {
                    "count": 1
                }
            },
            "displayName": "test condition",
            "name": "projects/tf-test/alertPolicies/3528831492076541324/conditions/3528831492076543949"
        },
        "condition_name": "test condition",
        "ended_at": 1621359336,
        "incident_id": "0.m2d61b3s6d5d",
        "metric": {
            "displayName": "CPU usage",
            "type": "compute.googleapis.com/instance/cpu/usage_time"
        },
        "policy_name": "test Alert Policy",
        "resource": {
            "labels": {
                "project_id": "tf-test"
            },
            "type": "gce_instance"
        },
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
        httplib2.Http = self._http_mock

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
        for bad_config in _BAD_CONFIG_PARAMS:     
            with self.assertRaises(service_handler.ConfigParamsError):
                handler.CheckConfigParams(bad_config)

    def testSendNotificationFailedDueToBadConfig(self):
        handler = service_handler.GchatHandler()
        for bad_config in _BAD_CONFIG_PARAMS:     
            _, status_code = handler.SendNotification(bad_config, _NOTIF)
            self.assertEqual(status_code, 400)

    def testSendNotificationFailedDueToUnexpectedCheckConfigParamsException(self):
        handler = service_handler.GchatHandler()
        # Set the config_param to None to cause exception.
        _, status_code = handler.SendNotification(None, _NOTIF) 
        self.assertEqual(status_code, 500)

    def testSendNotificationFormatTextFailedDuetoException(self):
        handler = service_handler.GchatHandler()
        config_params = _CONFIG_PARAMS.copy()
        self._http_obj_mock.request.side_effect = Exception('unknown exception')
        config_params['msg_format'] = 'text'
        _, status_code = handler.SendNotification(config_params, _NOTIF) 
        self.assertEqual(status_code, 400)
        self._http_obj_mock.request.assert_called_once()

    def testSendNotificationFormatTextSucceed(self):
        handler = service_handler.GchatHandler()
        config_params = _CONFIG_PARAMS.copy()
        config_params['msg_format'] = 'text'
        self._http_obj_mock.request.return_value = httplib2.Response({'status': 200}), b'OK'
        _, status_code = handler.SendNotification(config_params, _NOTIF) 
        self.assertEqual(status_code, 200)
        expected_body = (
            '{"text": "{\\"incident\\": {\\"condition\\": {\\"conditionThreshold\\": '
            '{\\"aggregations\\": [{\\"alignmentPeriod\\": \\"60s\\", '
            '\\"crossSeriesReducer\\": \\"REDUCE_SUM\\", \\"perSeriesAligner\\":'
            ' \\"ALIGN_SUM\\"}], \\"comparison\\": \\"COMPARISON_GT\\", '
            '\\"duration\\": \\"60s\\", \\"filter\\": \\"metric.type=\\\\\\'
            '"compute.googleapis.com/instance/cpu/usage_time\\\\\\" AND '
            'resource.type=\\\\\\"gce_instance\\\\\\"\\", \\"trigger\\": '
            '{\\"count\\": 1}}, \\"displayName\\": \\"test condition\\", \\"name\\":'
            ' \\"projects/tf-test/alertPolicies/3528831492076541324/conditions/'
            '3528831492076543949\\"}, \\"condition_name\\": \\"test condition\\",'
            ' \\"ended_at\\": 1621359336, \\"incident_id\\": \\"0.m2d61b3s6d5d\\",'
            ' \\"metric\\": {\\"displayName\\": \\"CPU usage\\", \\"type\\": '
            '\\"compute.googleapis.com/instance/cpu/usage_time\\"}, \\"policy_name\\":'
            ' \\"test Alert Policy\\", \\"resource\\": {\\"labels\\": '
            '{\\"project_id\\": \\"tf-test\\"}, \\"type\\": \\"gce_instance\\"}, '
            '\\"resource_id\\": \\"\\", \\"resource_name\\": \\"tf-test VM Instance '
            'labels {project_id=tf-test}\\", \\"resource_type_display_name\\": \\"VM '
            'Instance\\", \\"started_at\\": 1620754533, \\"state\\": \\"closed\\", '
            '\\"summary\\": \\"CPU usage for tf-test VM Instance labels '
            '{project_id=tf-test} returned to normal with a value of 0.081.\\", '
            '\\"url\\": \\"https://console.cloud.google.com/monitoring/alerting/'
            'incidents/0.m2d61b3s6d5d?project=tf-test\\"}, \\"version\\": \\"1.2\\"}"}'
        )
        self._http_obj_mock.request.assert_called_once_with(
            uri='https://chat.123.com',
            method='POST',
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            body=expected_body,
        )

    def testSendNotificationFormatCardSucceed(self):
        handler = service_handler.GchatHandler()
        self._http_obj_mock.request.return_value = httplib2.Response({'status': 200}), b'OK'
        http_response, status_code = handler.SendNotification(_CONFIG_PARAMS, _NOTIF) 
        self.assertEqual(status_code, 200)
        self.assertEqual(http_response, 'OK')
        expected_body = (
            '{"cards": [{"sections": [{"widgets": [{"textParagraph": {"text":'
            ' "<b><font color=\\"#0000FF\\">Summary:</font></b> CPU usage for '
            'tf-test VM Instance labels {project_id=tf-test} returned to normal'
            ' with a value of 0.081., <br><b><font    color=\\"#0000FF\\">'
            'State:</font></b> closed"}}, {"textParagraph": {"text": '
            '"<b>Condition Display Name:</b> test condition <br><b>Start '
            'at:</b> 2021-05-11 17:35:33 (UTC)<br><b>Incident Labels:</b> '
            '{\'project_id\': \'tf-test\'}"}}, {"buttons": [{"textButton": '
            '{"text": "View Incident Details", "onClick": {"openLink": '
            '{"url": "https://console.cloud.google.com/monitoring/alerting/'
            'incidents/0.m2d61b3s6d5d?project=tf-test"}}}}]}]}]}]}'
        )
        self._http_obj_mock.request.assert_called_once_with(
            uri='https://chat.123.com',
            method='POST',
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            body=expected_body,
        )

    def testSendNotificationFormatTextNon200Status(self):
        handler = service_handler.GchatHandler()
        config_params = _CONFIG_PARAMS.copy()
        self._http_obj_mock.request.return_value = httplib2.Response({'status': 500}), b'Server error'
        config_params['msg_format'] = 'text'
        http_response, status_code = handler.SendNotification(config_params, _NOTIF) 
        self.assertEqual(status_code, 500)
        self.assertEqual(http_response, 'Server error')
        self._http_obj_mock.request.assert_called_once()

    def testSendNotificationFormatCardFailedDueToMissingField(self):
        missing_fields = ['condition', 'resource', 'url', 'state', 'summary']
        handler = service_handler.GchatHandler()
        self._http_obj_mock.request.return_value = httplib2.Response({'status': 200}), b'OK'
        for missing_field in missing_fields:
            notif = copy.deepcopy(_NOTIF)
            del notif['incident'][missing_field]

            _, status_code = handler.SendNotification(_CONFIG_PARAMS, notif) 
            self.assertEqual(status_code, 400)

    def testSendNotificationFormatCardStartedAtMissing(self):
        handler = service_handler.GchatHandler()
        notif_without_startime = copy.deepcopy(_NOTIF)
        del notif_without_startime['incident']['started_at']
        self._http_obj_mock.request.return_value = httplib2.Response({'status': 200}), b'OK'
        _, status_code = handler.SendNotification(_CONFIG_PARAMS, notif_without_startime) 
        self.assertEqual(status_code, 200)
        expected_body = (
            '{"cards": [{"sections": [{"widgets": [{"textParagraph": {"text":'
            ' "<b><font color=\\"#0000FF\\">Summary:</font></b> CPU usage for '
            'tf-test VM Instance labels {project_id=tf-test} returned to normal'
            ' with a value of 0.081., <br><b><font    color=\\"#0000FF\\">'
            'State:</font></b> closed"}}, {"textParagraph": {"text": '
            '"<b>Condition Display Name:</b> test condition <br><b>Start '
            'at:</b> <br><b>Incident Labels:</b> '
            '{\'project_id\': \'tf-test\'}"}}, {"buttons": [{"textButton": '
            '{"text": "View Incident Details", "onClick": {"openLink": '
            '{"url": "https://console.cloud.google.com/monitoring/alerting/'
            'incidents/0.m2d61b3s6d5d?project=tf-test"}}}}]}]}]}]}'
        )
        self._http_obj_mock.request.assert_called_once_with(
            uri='https://chat.123.com',
            method='POST',
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            body=expected_body,
        )


if __name__ == '__main__':
    unittest.main()
