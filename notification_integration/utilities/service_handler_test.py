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

"""Unit tests for service_handler.py."""
import copy
import json
import unittest
from unittest import mock
import httplib2
from utilities import service_handler

# A valid config map used in the tests.
_SERVICE_NAME_GCHAT = 'google_chat'
_SERVICE_NAME_TEAMS = 'microsoft_teams'
_HTTP_METHOD = 'POST'
_CONFIG_PARAMS_GCHAT = {
    'service_name': _SERVICE_NAME_GCHAT,
    'webhook_url': 'https://chat.123.com',
    'msg_format': 'card',
}
_CONFIG_PARAMS_TEAMS = {
    'service_name': _SERVICE_NAME_TEAMS,
    'webhook_url': 'https://outlook.office.com/webhook/.../IncomingWebhook/...',
    'msg_format': 'card',
}

_BAD_CONFIG_PARAMS_GCHAT = [
    {'service': _SERVICE_NAME_GCHAT},  # Bad service name key
    {'service_name': 'wrong_xxx'},  # Bad service name value
    {'service_name': 'google_chat', 'url': '123.com'},  # Bad url key
    {'service_name': 'google_chat', 'webhook_url': 123},  # Bad url value
    {
        'service_name': 'google_chat',
        'webhook_url': '123.com',
        'format': 'card',
    },  # Bad format key
    {
        'service_name': 'google_chat',
        'webhook_url': '123.com',
        'msg_format': 'video',
    },  # Bad format value
]
_BAD_CONFIG_PARAMS_TEAMS = [
    {'service': _SERVICE_NAME_TEAMS},  # Bad service name key
    {'service_name': 'wrong_xxx'},  # Bad service name value
    {'service_name': 'microsoft_teams', 'url': '123.com'},  # Bad url key
    {'service_name': 'microsoft_teams', 'webhook_url': 123},  # Bad url value
    {
        'service_name': 'microsoft_teams',
        'webhook_url': '123.com',
        'format': 'card',
    },  # Bad format key
    {
        'service_name': 'microsoft_teams',
        'webhook_url': '123.com',
        'msg_format': 'video',
    },  # Bad format value
    {},  # Missing service name
]


# Test notification json object.
_NOTIF = {
    'incident': {
        'condition': {
            'conditionThreshold': {
                'aggregations': [{
                    'alignmentPeriod': '60s',
                    'crossSeriesReducer': 'REDUCE_SUM',
                    'perSeriesAligner': 'ALIGN_SUM',
                }],
                'comparison': 'COMPARISON_GT',
                'duration': '60s',
                'filter': (
                    'metric.type="compute.googleapis.com/instance/cpu/usage_time"'
                    ' AND resource.type="gce_instance"'
                ),
                'trigger': {'count': 1},
            },
            'displayName': 'test condition',
            'name': 'projects/tf-test/alertPolicies/3528831492076541324/conditions/3528831492076543949',
        },
        'condition_name': 'test condition',
        'ended_at': 1621359336,
        'incident_id': '0.m2d61b3s6d5d',
        'metric': {
            'displayName': 'CPU usage',
            'type': 'compute.googleapis.com/instance/cpu/usage_time',
        },
        'policy_name': 'test Alert Policy',
        'resource': {
            'labels': {'project_id': 'tf-test'},
            'type': 'gce_instance',
        },
        'resource_id': '',
        'resource_name': 'tf-test VM Instance labels {project_id=tf-test}',
        'resource_type_display_name': 'VM Instance',
        'started_at': 1620754533,
        'state': 'closed',
        'summary': (
            'CPU usage for tf-test VM Instance labels {project_id=tf-test}'
            ' returned to normal with a value of 0.081.'
        ),
        'url': 'https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test',
    },
    'version': '1.2',
}


class ServiceHandlerTest(unittest.TestCase):

  def testAbstractServiceHandlerCannotBeInitialized(self):
    with self.assertRaises(TypeError):
      service_handler.ServiceHandler(_SERVICE_NAME_GCHAT)  # pylint: disable=abstract-class-instantiated


class HttpRequestBasedHandlerTest(unittest.TestCase):

  def testAbstractClassHttpRequestBasedHandlerCannotBeInitialized(self):
    with self.assertRaises(TypeError):
      service_handler.HttpRequestBasedHandler(_SERVICE_NAME_GCHAT, _HTTP_METHOD)  # pylint: disable=abstract-class-instantiated


class GchatHandlerTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self._http_obj_mock = mock.Mock()
    self._http_mock = mock.Mock(return_value=self._http_obj_mock)
    httplib2.Http = self._http_mock

  def testCheckServiceNameInConfigParamsFailed(self):
    handler = service_handler.GchatHandler()
    bad_configs = [
        {'service': _SERVICE_NAME_GCHAT},  # Bad service name key
        {'service_name': 'wrong_xxx'},  # Bad service name value
        {},  # Missing service name
    ]
    for bad_config in bad_configs:
      with self.assertRaises(service_handler.ConfigParamsError):
        handler.CheckServiceNameInConfigParams(bad_config)

  def testCheckConfigParamsFailed(self):
    handler = service_handler.GchatHandler()
    for bad_config in _BAD_CONFIG_PARAMS_GCHAT:
      with self.assertRaises(service_handler.ConfigParamsError):
        handler.CheckConfigParams(bad_config)

  def testSendNotificationFailedDueToBadConfig(self):
    handler = service_handler.GchatHandler()
    for bad_config in _BAD_CONFIG_PARAMS_GCHAT:
      _, status_code = handler.SendNotification(bad_config, _NOTIF)
      self.assertNotEqual(status_code, 200)

  def testSendNotificationFailedDueToUnexpectedCheckConfigParamsException(self):
    handler = service_handler.GchatHandler()
    _, status_code = handler.SendNotification(None, _NOTIF)
    self.assertEqual(status_code, 500)

  def testSendNotificationFormatTextFailedDueToException(self):
    handler = service_handler.GchatHandler()
    config_params = _CONFIG_PARAMS_GCHAT.copy()
    self._http_obj_mock.request.side_effect = Exception('unknown exception')
    config_params['msg_format'] = 'text'
    _, status_code = handler.SendNotification(config_params, _NOTIF)
    self.assertEqual(status_code, 500)
    self._http_obj_mock.request.assert_called_once()

  def testSendNotificationFormatTextSucceed(self):
    handler = service_handler.GchatHandler()
    config_params = _CONFIG_PARAMS_GCHAT.copy()
    config_params['msg_format'] = 'text'
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(config_params, _NOTIF)
    self.assertEqual(status_code, 200)
    expected_body = (
        '{"text": "{\\"incident\\": {\\"condition\\":'
        ' {\\"conditionThreshold\\": {\\"aggregations\\":'
        ' [{\\"alignmentPeriod\\": \\"60s\\", \\"crossSeriesReducer\\":'
        ' \\"REDUCE_SUM\\", \\"perSeriesAligner\\": \\"ALIGN_SUM\\"}],'
        ' \\"comparison\\": \\"COMPARISON_GT\\", \\"duration\\": \\"60s\\",'
        ' \\"filter\\":'
        ' \\"metric.type=\\\\\\"compute.googleapis.com/instance/cpu/usage_time\\\\\\"'
        ' AND resource.type=\\\\\\"gce_instance\\\\\\"\\", \\"trigger\\":'
        ' {\\"count\\": 1}}, \\"displayName\\": \\"test condition\\",'
        ' \\"name\\":'
        ' \\"projects/tf-test/alertPolicies/3528831492076541324/conditions/3528831492076543949\\"},'
        ' \\"condition_name\\": \\"test condition\\", \\"ended_at\\":'
        ' 1621359336, \\"incident_id\\": \\"0.m2d61b3s6d5d\\", \\"metric\\":'
        ' {\\"displayName\\": \\"CPU usage\\", \\"type\\":'
        ' \\"compute.googleapis.com/instance/cpu/usage_time\\"},'
        ' \\"policy_name\\": \\"test Alert Policy\\", \\"resource\\":'
        ' {\\"labels\\": {\\"project_id\\": \\"tf-test\\"}, \\"type\\":'
        ' \\"gce_instance\\"}, \\"resource_id\\": \\"\\", \\"resource_name\\":'
        ' \\"tf-test VM Instance labels {project_id=tf-test}\\",'
        ' \\"resource_type_display_name\\": \\"VM Instance\\",'
        ' \\"started_at\\": 1620754533, \\"state\\": \\"closed\\",'
        ' \\"summary\\": \\"CPU usage for tf-test VM Instance labels'
        ' {project_id=tf-test} returned to normal with a value of 0.081.\\",'
        ' \\"url\\":'
        ' \\"https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test\\"},'
        ' \\"version\\": \\"1.2\\"}"}'
    )
    self._http_obj_mock.request.assert_called_with(
        uri='https://chat.123.com',
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardSucceed(self):
    handler = service_handler.GchatHandler()
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    expected_body = json.dumps({
        'cards': [{
            'sections': [{
                'widgets': [
                    {
                        'textParagraph': {
                            'text': (
                                '<b><font'
                                ' color="{header_color}">Summary:</font></b>'
                                ' CPU usage for tf-test VM Instance labels'
                                ' {project_id=tf-test} returned to normal with'
                                ' a value of 0.081., <br><b><font'
                                ' color="#0000FF">State:</font></b> closed'
                            )
                        }
                    },
                    {
                        'textParagraph': {
                            'text': (
                                '<b>Condition Display Name:</b> test condition'
                                ' <br><b>Start at:</b> 2021-05-11 17:35:33'
                                ' (UTC)<br><b>Incident Labels:</b>'
                                " {'project_id': 'tf-test'}"
                            )
                        }
                    },
                    {
                        'buttons': [{
                            'textButton': {
                                'text': 'View Incident Details',
                                'onClick': {
                                    'openLink': {
                                        'url': 'https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test'
                                    }
                                },
                            }
                        }]
                    },
                ]
            }]
        }]
    })

    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_GCHAT, _NOTIF
    )

    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')

    # Ensure the body matches
    self._http_obj_mock.request.assert_called_with(
        uri='https://chat.123.com',
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardFailedDueToMissingField(self):
    missing_fields = ['condition', 'resource', 'url', 'state', 'summary']
    handler = service_handler.GchatHandler()
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    for missing_field in missing_fields:
      notif = copy.deepcopy(_NOTIF)
      del notif['incident'][missing_field]

      _, status_code = handler.SendNotification(_CONFIG_PARAMS_GCHAT, notif)
      self.assertNotEqual(status_code, 200)

  def testSendNotificationFormatCardStartedAtMissing(self):
    handler = service_handler.GchatHandler()
    notif_without_startime = copy.deepcopy(_NOTIF)
    del notif_without_startime['incident']['started_at']
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_GCHAT, notif_without_startime
    )
    self.assertEqual(status_code, 200)
    expected_body = (
        '{"cards": [{"sections": [{"widgets": [{"textParagraph": {"text":'
        ' "<b><font color=\\"{header_color}\\">Summary:</font></b> CPU usage'
        ' for '
        'tf-test VM Instance labels {project_id=tf-test} returned to normal'
        ' with a value of 0.081., <br><b><font'
        ' color=\\"#0000FF\\">State:</font></b> closed"}}, '
        '{"textParagraph": {"text": "<b>Condition Display Name:</b> test'
        ' condition <br><b>Start at:</b> <br>'
        "<b>Incident Labels:</b> {'project_id': 'tf-test'}\"}}, {\"buttons\":"
        ' [{"textButton": {"text": "View Incident Details", "onClick":'
        ' {"openLink": {"url":'
        ' "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test"}}}}]}]}]}]}'
    )
    self._http_obj_mock.request.assert_called_with(
        uri='https://chat.123.com',
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )


class MSTeamsHandlerTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self._http_obj_mock = mock.Mock()
    self._http_mock = mock.Mock(return_value=self._http_obj_mock)
    httplib2.Http = self._http_mock

  def testCheckServiceNameInConfigParamsFailed(self):
    handler = service_handler.MSTeamsHandler()
    for bad_config in _BAD_CONFIG_PARAMS_TEAMS:
      with self.assertRaises(service_handler.ConfigParamsError):
        handler.CheckServiceNameInConfigParams(bad_config)

  def testCheckConfigParamsFailed(self):
    handler = service_handler.MSTeamsHandler()
    for bad_config in _BAD_CONFIG_PARAMS_TEAMS:
      with self.assertRaises(service_handler.ConfigParamsError):
        handler.CheckConfigParams(bad_config)

  def testSendNotificationFailedDueToBadConfig(self):
    handler = service_handler.MSTeamsHandler()
    for bad_config in _BAD_CONFIG_PARAMS_TEAMS:
      _, status_code = handler.SendNotification(bad_config, _NOTIF)
      self.assertNotEqual(status_code, 200)

  def testSendNotificationFailedDueToUnexpectedCheckConfigParamsException(self):
    handler = service_handler.MSTeamsHandler()
    _, status_code = handler.SendNotification(None, _NOTIF)
    self.assertEqual(status_code, 500)

  def testSendNotificationFormatTextFailedDueToException(self):
    handler = service_handler.MSTeamsHandler()
    config_params = _CONFIG_PARAMS_TEAMS.copy()
    self._http_obj_mock.request.side_effect = Exception('unknown exception')
    config_params['msg_format'] = 'text'
    _, status_code = handler.SendNotification(config_params, _NOTIF)
    self.assertEqual(status_code, 500)
    self._http_obj_mock.request.assert_called_once()

  def testSendNotificationFormatTextSucceed(self):
    handler = service_handler.MSTeamsHandler()
    config_params = _CONFIG_PARAMS_TEAMS.copy()
    config_params['msg_format'] = 'text'
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(config_params, _NOTIF)
    self.assertEqual(status_code, 200)
    expected_body = (
        '{"text": "{\\"incident\\": {\\"condition\\":'
        ' {\\"conditionThreshold\\": {\\"aggregations\\":'
        ' [{\\"alignmentPeriod\\": \\"60s\\", \\"crossSeriesReducer\\":'
        ' \\"REDUCE_SUM\\", \\"perSeriesAligner\\": \\"ALIGN_SUM\\"}],'
        ' \\"comparison\\": \\"COMPARISON_GT\\", \\"duration\\": \\"60s\\",'
        ' \\"filter\\":'
        ' \\"metric.type=\\\\\\"compute.googleapis.com/instance/cpu/usage_time\\\\\\"'
        ' AND resource.type=\\\\\\"gce_instance\\\\\\"\\", \\"trigger\\":'
        ' {\\"count\\": 1}}, \\"displayName\\": \\"test condition\\",'
        ' \\"name\\":'
        ' \\"projects/tf-test/alertPolicies/3528831492076541324/conditions/3528831492076543949\\"},'
        ' \\"condition_name\\": \\"test condition\\", \\"ended_at\\":'
        ' 1621359336, \\"incident_id\\": \\"0.m2d61b3s6d5d\\", \\"metric\\":'
        ' {\\"displayName\\": \\"CPU usage\\", \\"type\\":'
        ' \\"compute.googleapis.com/instance/cpu/usage_time\\"},'
        ' \\"policy_name\\": \\"test Alert Policy\\", \\"resource\\":'
        ' {\\"labels\\": {\\"project_id\\": \\"tf-test\\"}, \\"type\\":'
        ' \\"gce_instance\\"}, \\"resource_id\\": \\"\\", \\"resource_name\\":'
        ' \\"tf-test VM Instance labels {project_id=tf-test}\\",'
        ' \\"resource_type_display_name\\": \\"VM Instance\\",'
        ' \\"started_at\\": 1620754533, \\"state\\": \\"closed\\",'
        ' \\"summary\\": \\"CPU usage for tf-test VM Instance labels'
        ' {project_id=tf-test} returned to normal with a value of 0.081.\\",'
        ' \\"url\\":'
        ' \\"https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test\\"},'
        ' \\"version\\": \\"1.2\\"}"}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri=_CONFIG_PARAMS_TEAMS['webhook_url'],
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardSucceed(self):
    handler = service_handler.MSTeamsHandler()
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, _NOTIF
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "test Alert Policy",'
        ' "weight": "Bolder", "size": "Medium"}, {"type": "TextBlock", "text":'
        ' "CPU usage for tf-test VM Instance labels {project_id=tf-test}'
        ' returned to normal with a value of 0.081.", "isSubtle": true, "wrap":'
        ' true}, {"type": "ColumnSet", "columns": [{"type": "Column", "width":'
        ' "auto", "items": [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "closed", "color": "Green", "size": "Small", "spacing": "None",'
        ' "wrap": true}]}, {"type": "Column", "width": "auto", "items":'
        ' [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url":'
        ' "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test",'
        ' "isPrimary": true}, {"type": "Action.ShowCard", "title": "Additional'
        ' details", "card": {"type": "AdaptiveCard", "body": [{"type":'
        ' "Container", "items": [{"type": "TextBlock", "text": "Additional'
        ' details", "weight": "Bolder", "size": "Medium"}, {"type":'
        ' "TextBlock", "text": "", "wrap": true, "separator": false}, {"type":'
        ' "TextBlock", "text": "Labels", "size": "Small", "weight": "Bolder",'
        ' "spacing": "Large"}, {"type": "FactSet", "facts": [{"title":'
        ' "metric_type", "value": "usage_time"}, {"title": "project_id",'
        ' "value": "tf-test"}], "spacing": "Small"}]}]}}]}], "$schema":'
        ' "http://adaptivecards.io/schemas/adaptive-card.json", "version":'
        ' "1.5"}}]}'
    )

    self._http_obj_mock.request.assert_called_with(
        uri=_CONFIG_PARAMS_TEAMS['webhook_url'],
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardSucceedWithDocumentationAndQuickLinks(self):
    handler = service_handler.MSTeamsHandler()
    notif_without_startime = copy.deepcopy(_NOTIF)
    del notif_without_startime['incident']['started_at']
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    _, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_without_startime
    )
    self.assertEqual(status_code, 200)
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "test Alert Policy",'
        ' "weight": "Bolder", "size": "Medium"}, {"type": "TextBlock", "text":'
        ' "CPU usage for tf-test VM Instance labels {project_id=tf-test}'
        ' returned to normal with a value of 0.081.", "isSubtle": true, "wrap":'
        ' true}, {"type": "ColumnSet", "columns": [{"type": "Column", "width":'
        ' "auto", "items": [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "closed", "color": "Green", "size": "Small", "spacing": "None",'
        ' "wrap": true}]}, {"type": "Column", "width": "auto", "items":'
        ' [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url":'
        ' "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test",'
        ' "isPrimary": true}, {"type": "Action.ShowCard", "title": "Additional'
        ' details", "card": {"type": "AdaptiveCard", "body": [{"type":'
        ' "Container", "items": [{"type": "TextBlock", "text": "Additional'
        ' details", "weight": "Bolder", "size": "Medium"}, {"type":'
        ' "TextBlock", "text": "", "wrap": true, "separator": false}, {"type":'
        ' "TextBlock", "text": "Labels", "size": "Small", "weight": "Bolder",'
        ' "spacing": "Large"}, {"type": "FactSet", "facts": [{"title":'
        ' "metric_type", "value": "usage_time"}, {"title": "project_id",'
        ' "value": "tf-test"}], "spacing": "Small"}]}]}}]}], "$schema":'
        ' "http://adaptivecards.io/schemas/adaptive-card.json", "version":'
        ' "1.5"}}]}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri=_CONFIG_PARAMS_TEAMS['webhook_url'],
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardSucceedWithoutDocumentationAndQuickLinks(
      self,
  ):
    handler = service_handler.MSTeamsHandler()
    notif_without_docs_links = copy.deepcopy(_NOTIF)
    notif_without_docs_links['incident']['documentation'] = {
        'content': '',
        'links': [],
    }
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_without_docs_links
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "test Alert Policy",'
        ' "weight": "Bolder", "size": "Medium"}, {"type": "TextBlock", "text":'
        ' "CPU usage for tf-test VM Instance labels {project_id=tf-test}'
        ' returned to normal with a value of 0.081.", "isSubtle": true, "wrap":'
        ' true}, {"type": "ColumnSet", "columns": [{"type": "Column", "width":'
        ' "auto", "items": [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "closed", "color": "Green", "size": "Small", "spacing": "None",'
        ' "wrap": true}]}, {"type": "Column", "width": "auto", "items":'
        ' [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url":'
        ' "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test",'
        ' "isPrimary": true}, {"type": "Action.ShowCard", "title": "Additional'
        ' details", "card": {"type": "AdaptiveCard", "body": [{"type":'
        ' "Container", "items": [{"type": "TextBlock", "text": "Additional'
        ' details", "weight": "Bolder", "size": "Medium"}, {"type":'
        ' "TextBlock", "text": "**Quick links:** ", "wrap": true, "separator":'
        ' true}, {"type": "TextBlock", "text": "Labels", "size": "Small",'
        ' "weight": "Bolder", "spacing": "Large"}, {"type": "FactSet", "facts":'
        ' [{"title": "metric_type", "value": "usage_time"}, {"title":'
        ' "project_id", "value": "tf-test"}], "spacing": "Small"}]}]}}]}],'
        ' "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",'
        ' "version": "1.5"}}]}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri=_CONFIG_PARAMS_TEAMS['webhook_url'],
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardSucceedWithOnlyDocumentation(self):
    handler = service_handler.MSTeamsHandler()
    notif_with_docs_only = copy.deepcopy(_NOTIF)
    notif_with_docs_only['incident']['documentation'] = {
        'content': 'Some documentation content',
        'links': [],
    }
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_with_docs_only
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "test Alert Policy",'
        ' "weight": "Bolder", "size": "Medium"}, {"type": "TextBlock", "text":'
        ' "CPU usage for tf-test VM Instance labels {project_id=tf-test}'
        ' returned to normal with a value of 0.081.", "isSubtle": true, "wrap":'
        ' true}, {"type": "ColumnSet", "columns": [{"type": "Column", "width":'
        ' "auto", "items": [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "closed", "color": "Green", "size": "Small", "spacing": "None",'
        ' "wrap": true}]}, {"type": "Column", "width": "auto", "items":'
        ' [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url":'
        ' "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test",'
        ' "isPrimary": true}, {"type": "Action.ShowCard", "title": "Additional'
        ' details", "card": {"type": "AdaptiveCard", "body": [{"type":'
        ' "Container", "items": [{"type": "TextBlock", "text": "Additional'
        ' details", "weight": "Bolder", "size": "Medium"}, {"type":'
        ' "TextBlock", "text": "**Quick links:** ", "wrap": true, "separator":'
        ' true}, {"type": "TextBlock", "text": "Labels", "size": "Small",'
        ' "weight": "Bolder", "spacing": "Large"}, {"type": "FactSet", "facts":'
        ' [{"title": "metric_type", "value": "usage_time"}, {"title":'
        ' "project_id", "value": "tf-test"}], "spacing": "Small"}, {"type":'
        ' "TextBlock", "text": "Documentation", "size": "Small", "weight":'
        ' "Bolder", "spacing": "Large"}, {"type": "TextBlock", "text": "Some'
        ' documentation content", "spacing": "Small", "wrap": true}]}]}}]}],'
        ' "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",'
        ' "version": "1.5"}}]}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri=_CONFIG_PARAMS_TEAMS['webhook_url'],
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardSucceedWithOnlyQuickLinks(self):
    handler = service_handler.MSTeamsHandler()
    notif_with_links_only = copy.deepcopy(_NOTIF)
    notif_with_links_only['incident']['documentation'] = {
        'content': '',
        'links': [
            {'DisplayName': 'playbook updated2', 'URL': 'https://google.com'},
            {'DisplayName': 'playbook updated3', 'URL': 'https://google.com'},
        ],
    }
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_with_links_only
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "test Alert Policy",'
        ' "weight": "Bolder", "size": "Medium"}, {"type": "TextBlock", "text":'
        ' "CPU usage for tf-test VM Instance labels {project_id=tf-test}'
        ' returned to normal with a value of 0.081.", "isSubtle": true, "wrap":'
        ' true}, {"type": "ColumnSet", "columns": [{"type": "Column", "width":'
        ' "auto", "items": [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "closed", "color": "Green", "size": "Small", "spacing": "None",'
        ' "wrap": true}]}, {"type": "Column", "width": "auto", "items":'
        ' [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url":'
        ' "https://console.cloud.google.com/monitoring/alerting/incidents/0.m2d61b3s6d5d?project=tf-test",'
        ' "isPrimary": true}, {"type": "Action.ShowCard", "title": "Additional'
        ' details", "card": {"type": "AdaptiveCard", "body": [{"type":'
        ' "Container", "items": [{"type": "TextBlock", "text": "Additional'
        ' details", "weight": "Bolder", "size": "Medium"}, {"type":'
        ' "TextBlock", "text": "**Quick links:** [playbook'
        ' updated2](https://google.com) \\u2022 [playbook'
        ' updated3](https://google.com)", "wrap": true, "separator": true},'
        ' {"type": "TextBlock", "text": "Labels", "size": "Small", "weight":'
        ' "Bolder", "spacing": "Large"}, {"type": "FactSet", "facts":'
        ' [{"title": "metric_type", "value": "usage_time"}, {"title":'
        ' "project_id", "value": "tf-test"}], "spacing": "Small"}]}]}}]}],'
        ' "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",'
        ' "version": "1.5"}}]}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri='https://outlook.office.com/webhook/.../IncomingWebhook/...',
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationWithEmptyIncident(self):
    handler = service_handler.MSTeamsHandler()
    notif_empty_incident = {'incident': {}}
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_empty_incident
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "N/A", "weight": "Bolder",'
        ' "size": "Medium"}, {"type": "TextBlock", "text": "N/A", "isSubtle":'
        ' true, "wrap": true}, {"type": "ColumnSet", "columns": [{"type":'
        ' "Column", "width": "auto", "items": [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "color": "Green", "size": "Small", "spacing": "None", "wrap":'
        ' true}]}, {"type": "Column", "width": "auto", "items": [{"type":'
        ' "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url": "N/A", "isPrimary":'
        ' true}, {"type": "Action.ShowCard", "title": "Additional details",'
        ' "card": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "Additional details",'
        ' "weight": "Bolder", "size": "Medium"}, {"type": "TextBlock", "text":'
        ' "", "wrap": true, "separator": false}, {"type": "TextBlock", "text":'
        ' "Labels", "size": "Small", "weight": "Bolder", "spacing": "Large"},'
        ' {"type": "FactSet", "facts": [{"title": "metric_type", "value":'
        ' "A"}], "spacing": "Small"}]}]}}]}], "$schema":'
        ' "http://adaptivecards.io/schemas/adaptive-card.json", "version":'
        ' "1.5"}}]}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri='https://outlook.office.com/webhook/.../IncomingWebhook/...',
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationWithOnlyRequiredFields(self):
    handler = service_handler.MSTeamsHandler()
    notif_only_required = {
        'incident': {
            'condition_name': 'test condition',
            'summary': 'Test summary',
            'state': 'open',
            'url': 'https://test.url',
        }
    }
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_only_required
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')
    expected_body = (
        '{"type": "message", "attachments": [{"contentType":'
        ' "application/vnd.microsoft.card.adaptive", "contentUrl": null,'
        ' "content": {"type": "AdaptiveCard", "body": [{"type": "Container",'
        ' "items": [{"type": "TextBlock", "text": "N/A", "weight": "Bolder",'
        ' "size": "Medium"}, {"type": "TextBlock", "text": "Test summary",'
        ' "isSubtle": true, "wrap": true}, {"type": "ColumnSet", "columns":'
        ' [{"type": "Column", "width": "auto", "items": [{"type": "Image",'
        ' "url": "https://ssl.gstatic.com/cloud-monitoring/incident_open.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "open", "color": "Attention", "size": "Small", "spacing": "None",'
        ' "wrap": true}]}, {"type": "Column", "width": "auto", "items":'
        ' [{"type": "Image", "url":'
        ' "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",'
        ' "width": "18px", "height": "18px", "spacing": "None"}]}, {"type":'
        ' "Column", "width": "auto", "items": [{"type": "TextBlock", "text":'
        ' "N/A", "size": "Small", "weight": "Default", "spacing": "Small",'
        ' "wrap": true}]}]}]}, {"type": "ActionSet", "actions": [{"type":'
        ' "Action.OpenUrl", "title": "View alert", "url": "https://test.url",'
        ' "isPrimary": true}, {"type": "Action.ShowCard", "title": "Additional'
        ' details", "card": {"type": "AdaptiveCard", "body": [{"type":'
        ' "Container", "items": [{"type": "TextBlock", "text": "Additional'
        ' details", "weight": "Bolder", "size": "Medium"}, {"type":'
        ' "TextBlock", "text": "", "wrap": true, "separator": false}, {"type":'
        ' "TextBlock", "text": "Labels", "size": "Small", "weight": "Bolder",'
        ' "spacing": "Large"}, {"type": "FactSet", "facts": [{"title":'
        ' "metric_type", "value": "A"}], "spacing": "Small"}]}]}}]}],'
        ' "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",'
        ' "version": "1.5"}}]}'
    )
    self._http_obj_mock.request.assert_called_once_with(
        uri='https://outlook.office.com/webhook/.../IncomingWebhook/...',
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=expected_body,
    )

  def testSendNotificationFormatCardStillSucceedWithMissingRequiredField(self):
    required_fields = ['condition_name', 'summary', 'state', 'url']
    handler = service_handler.MSTeamsHandler()
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    for required_field in required_fields:
      notif = copy.deepcopy(_NOTIF)
      del notif['incident'][required_field]

      _, status_code = handler.SendNotification(_CONFIG_PARAMS_TEAMS, notif)
      self.assertEqual(status_code, 200)

  def testSendNotificationWithDifferentSeverityLevels(self):
    handler = service_handler.MSTeamsHandler()
    severity_levels = ['Critical', 'Error', 'Warning', 'No severity']
    for severity in severity_levels:
      notif_with_severity = copy.deepcopy(_NOTIF)
      notif_with_severity['incident']['severity'] = severity
      self._http_obj_mock.request.return_value = (
          httplib2.Response({'status': 200}),
          b'OK',
      )
      http_response, status_code = handler.SendNotification(
          _CONFIG_PARAMS_TEAMS, notif_with_severity
      )
      self.assertEqual(status_code, 200)
      self.assertEqual(http_response, 'OK')

  def testSendNotificationWithSpecialCharacters(self):
    handler = service_handler.MSTeamsHandler()
    notif_with_special_chars = copy.deepcopy(_NOTIF)
    notif_with_special_chars['incident'][
        'summary'
    ] = 'CPU usage <script>alert("test")</script>'
    notif_with_special_chars['incident']['resource']['labels'].update(
        {'special_label': '<b>bold</b>'}
    )
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_with_special_chars
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')

  def testSendNotificationWithDifferentIncidentStates(self):
    handler = service_handler.MSTeamsHandler()
    incident_states = ['open', 'closed']
    for state in incident_states:
      notif_with_state = copy.deepcopy(_NOTIF)
      notif_with_state['incident']['state'] = state
      self._http_obj_mock.request.return_value = (
          httplib2.Response({'status': 200}),
          b'OK',
      )
      http_response, status_code = handler.SendNotification(
          _CONFIG_PARAMS_TEAMS, notif_with_state
      )
      self.assertEqual(status_code, 200)
      self.assertEqual(http_response, 'OK')

  def testSendNotificationWithLargeNumberOfLabels(self):
    handler = service_handler.MSTeamsHandler()
    notif_with_many_labels = copy.deepcopy(_NOTIF)
    notif_with_many_labels['incident']['resource']['labels'].update(
        {f'label_{i}': f'value_{i}' for i in range(100)}
    )
    self._http_obj_mock.request.return_value = (
        httplib2.Response({'status': 200}),
        b'OK',
    )
    http_response, status_code = handler.SendNotification(
        _CONFIG_PARAMS_TEAMS, notif_with_many_labels
    )
    self.assertEqual(status_code, 200)
    self.assertEqual(http_response, 'OK')


if __name__ == '__main__':
  unittest.main()
