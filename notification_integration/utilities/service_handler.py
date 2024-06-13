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

"""Module that provides handlers to integrate with 3rd-party services."""
import abc
import datetime
import json
import logging
from typing import Any, Dict, Text, Tuple
import httplib2
from utilities import config_server


class Error(Exception):
  """Base error for this module."""

  pass


class ConfigParamsError(Error):
  """The config parameters used to create a handler are invalid."""

  pass


class ServiceHandler(abc.ABC):
  """Abstract base class that represents a 3rd-party service handler."""

  def __init__(self, service_name: Text):
    # service_name is the name of the service this handler is to integrate with.
    self._service_name = service_name

  def CheckServiceNameInConfigParams(self, config_params: Dict[str, Any]):
    """Ensures 'service_name' is in the config_params and set correctly."""
    if not (
        'service_name' in config_params
        and config_params['service_name'] == self._service_name
    ):
      raise ConfigParamsError(
          f'service_name is not set or different from {self._service_name} :'
          f' {config_params}'
      )

  @abc.abstractmethod
  def CheckConfigParams(self, config_params: Dict[Text, Any]):
    """Checks if the given config params is a valid one that has all the necessary configs.

    Args:
       config_params: A dictionary that includes information about where/how to
         send notifications to a 3rd-party service.

    Raises:
        Any exception raised when sending the notificaton.
    """
    pass

  @abc.abstractmethod
  def SendNotification(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Tuple[Text, int]:
    """Sends a notification to a 3rd-party service endpoint.

    It uses the config_params to get the information about where/how to send
    notifications to a 3rd-party service,
    converts the received message, which is a dictionary containing a json
    object defined at
    https://cloud.google.com/monitoring/support/notification-options (see Schema
    structure), into api call/http request, and sends the requests to the
    service endpoint.

    Args:
       config_params: A dictionary that includes information about where/how to
         send notifications to a 3rd-party service.
       notification: An incoming alerting message to forward.

    Returns:
       A tuple (response_msg, status_code), where response_msg is the response
       message string and status_code is the status code to be returned.

    Raises:
        Any exception raised when sending the notificaton.
    """
    pass


class HttpRequestBasedHandler(ServiceHandler, abc.ABC):
  """Abstract base class for handlers that use httplib2.Http to send requests."""

  def __init__(self, service_name: Text, http_method: Text):
    super(HttpRequestBasedHandler, self).__init__(service_name)
    self._http_method = http_method

  @abc.abstractmethod
  def _BuildHttpRequestBody(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Text:
    """Converts the notification into a http request body.

    Args:
        config_params: A dictionary that includes information about where/how to
          send notifications to a 3rd-party service.
        notification: An incoming alerting message to forward.

    Returns:
        A json dump (str) of the created message json object.

    Raises:
        Any exception raised during the process.
    """
    pass

  @abc.abstractmethod
  def _BuildHttpRequestHeaders(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> Dict[Text, Any]:
    """Builds the Http request headers.

    Args:
        config_params: A dictionary that includes information about where/how to
          send notifications to a 3rd-party service.
        notification: An incoming alerting message to forward.

    Returns:
        A http request headers to be included in the outgoing http request.

    Raises:
        Any exception raised during the process.
    """
    pass

  @abc.abstractmethod
  def _GetHttpUrl(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> Text:
    """Gets the Http URL from the configuration parameters.

    Args:
        config_params: A dictionary that includes information about where/how to
          send notifications to a 3rd-party service.
        notification: An incoming alerting message to forward.

    Returns:
       A http URL used to sent the http request.

    Raises:
        Any exception raised during the process.
    """
    pass

  def _SendHttpRequest(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> Tuple[httplib2.Response, Text]:
    """Sends a http request to a 3rd-party service via a http request."""
    http_url = self._GetHttpUrl(config_params, notification)
    messages_headers = self._BuildHttpRequestHeaders(
        config_params, notification
    )
    message_body = self._BuildHttpRequestBody(config_params, notification)

    http_obj = httplib2.Http()

    # content is a bytes object.
    http_response, content = http_obj.request(
        uri=http_url,
        method=self._http_method,
        headers=messages_headers,
        body=message_body,
    )
    return http_response, content.decode('utf-8')


class GchatHandler(HttpRequestBasedHandler):
  """Handler that integrates the Google alerting pubsub chananel with the Google Chat service.

  It converts a received notification into a well-formated Google Chat message
  and sends it to the
  configed Google Chat room. The config parameter its needs is the Google chat
  room webhook URL.
  """

  # The handler supports two formats: text and card, see https://developers.google.com/chat/api/guides/message-formats/basic and https://developers.google.com/chat/api/guides/message-formats/cards and
  _SUPPORTED_FORMAT = set(['text', 'card'])
  _RED_COLOR = '#FF0000'  # Red for open issues.
  _BLUE_COLOR = '#0000FF'  # Blue for closed issues.
  _GCHAT_SERVICE_NAME = 'google_chat'
  _GCHAT_HTTP_METHOD = 'POST'
  _URL_PARAM_NAME = 'webhook_url'
  _FORMAT_PARAM_NAME = 'msg_format'

  def __init__(self):
    super(GchatHandler, self).__init__(
        self._GCHAT_SERVICE_NAME, self._GCHAT_HTTP_METHOD
    )

  def CheckConfigParams(self, config_params: Dict[Text, Any]):
    """Checks if the given config params is a valid one that has all the necessary configs.

    The google chat handler  needs the webhook url of a google chat room and the
    format setting to forward the notifications.
    """
    self.CheckServiceNameInConfigParams(config_params)

    # The google chat room webhook url is needed to send the requests.
    if not (
        self._URL_PARAM_NAME in config_params
        and isinstance(config_params[self._URL_PARAM_NAME], str)
    ):
      raise ConfigParamsError(
          f'{self._URL_PARAM_NAME} is not set or not a string: {config_params}'
      )

    if not (
        self._FORMAT_PARAM_NAME in config_params
        and config_params[self._FORMAT_PARAM_NAME] in self._SUPPORTED_FORMAT
    ):
      raise ConfigParamsError(
          f'{self._FORMAT_PARAM_NAME} is not set or not a valid option:'
          f' {config_params}'
      )

  def _GetHttpUrl(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Text:
    return config_params[self._URL_PARAM_NAME]

  def _BuildHttpRequestHeaders(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Dict[Text, Any]:
    http_headers = {'Content-Type': 'application/json; charset=UTF-8'}
    return http_headers

  def _BuildHttpRequestBody(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Text:
    format = config_params['msg_format']
    """Converts the notification into a http request body."""
    if format == 'text':
      message_body = {'text': json.dumps(notification)}
      return json.dumps(message_body)

    assert format == 'card'
    try:
      started_time = notification['incident'].get('started_at')
      if started_time:
        started_time = datetime.datetime.utcfromtimestamp(int(started_time))
        started_time_str = started_time.strftime('%Y-%m-%d %H:%M:%S (UTC)')
      else:
        started_time_str = ''

      incident_display_name = notification['incident']['condition'][
          'displayName'
      ]
      incident_resource_labels = notification['incident']['resource']['labels']
      incident_url = notification['incident']['url']
      incident_state = notification['incident']['state']
      header_color = self._BLUE_COLOR
      if incident_state == 'open':
        header_color = self._RED_COLOR

      incident_ended_at = notification['incident'].get('ended_at')
      if incident_ended_at:
        incident_ended_at = datetime.datetime.utcfromtimestamp(
            int(incident_ended_at)
        )
      else:
        incident_ended_at = ''
      incident_summary = notification['incident']['summary']
    except:
      logging.error(f'failed to get notification fields {notification}')
      raise

    # Set the alert severity level if it is set in the user labels.
    try:
      incident_severity = notification['incident']['policy_user_labels'][
          'severity'
      ]
      incident_severity_display_str = (
          f', <br><b><font    color="{header_color}">Severity:</font></b>'
          f' {incident_severity}'
      )
    except:
      logging.error(
          f'Failed to extract the severity level info : {notification}'
      )
      incident_severity_display_str = ''

    message_body = {
        'cards': [{
            'sections': [{
                'widgets': [
                    {
                        'textParagraph': {
                            'text': (
                                '<b><font'
                                f' color="{header_color}">Summary:</font></b>'
                                f' {incident_summary}, <br><b><font   '
                                f' color="{header_color}">State:</font></b>'
                                f' {incident_state}{incident_severity_display_str}'
                            )
                        }
                    },
                    {
                        'textParagraph': {
                            'text': (
                                '<b>Condition Display Name:</b>'
                                f' {incident_display_name} <br><b>Start at:</b>'
                                f' {started_time_str}<br><b>Incident'
                                f' Labels:</b> {incident_resource_labels}'
                            )
                        }
                    },
                    {
                        'buttons': [{
                            'textButton': {
                                'text': 'View Incident Details',
                                'onClick': {
                                    'openLink': {'url': f'{incident_url}'}
                                },
                            }
                        }]
                    },
                ]
            }]
        }]
    }
    return json.dumps(message_body)

  def SendNotification(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Tuple[Text, int]:
    """Sends a notification to a Google chat room."""
    try:
      self.CheckConfigParams(config_params)
    except ConfigParamsError as err:
      logging.error(f'Failed to send the notification: {err}')
      return (str(err), 400)
    except BaseException as err:
      logging.error(f'Failed to send the notification: {err}')
      return (str(err), 500)

    try:
      logging.info(f'Sending the notification: {notification}')
      # content is of type bytes.
      http_response, content = self._SendHttpRequest(
          config_params, notification
      )
      logging.info(f'Successfully sent the notification: {http_response}')
    except BaseException as err:
      logging.error(f'Failed to send the notification: {err}')
      return (str(err), 400)
    return (content, http_response.status)
