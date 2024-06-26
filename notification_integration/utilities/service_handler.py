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

"""Module that provides handlers to integrate with 3rd-party services."""
import abc
import datetime
import json
import logging
from typing import Any, Dict, Text, Tuple
import httplib2


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
        "service_name" in config_params
        and config_params["service_name"] == self._service_name
    ):
      raise ConfigParamsError(
          f"service_name is not set or different from {self._service_name}:"
          f" {config_params}"
      )

  @abc.abstractmethod
  def CheckConfigParams(self, config_params: Dict[Text, Any]):
    """Checks if the given config params is a valid one that has all the necessary configs.

    Args:
       config_params: A dictionary that includes information about where/how to
         send notifications to a 3rd-party service.

    Raises:
        Any exception raised when sending the notification.
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
        Any exception raised when sending the notification.
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
       A http URL used to send the http request.

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
    return http_response, content.decode("utf-8")


class GchatHandler(HttpRequestBasedHandler):
  """Handler that integrates the Google alerting pubsub channel with the Google Chat service.

  It converts a received notification into a well-formatted Google Chat message
  and sends it to the configured Google Chat room. The config parameter it needs
  is the Google chat room webhook URL.
  """

  # The handler supports two formats: text and card, see
  # https://developers.google.com/chat/api/guides/message-formats/basic
  # and https://developers.google.com/chat/api/guides/message-formats/cards
  _SUPPORTED_FORMAT = set(["text", "card"])
  _OPEN_ISSUE_HEADER_COLOR = "#FF0000"  # Red for open issues.
  _CLOSED_ISSUE_HEADER_COLOR = "#0000FF"  # Blue for closed issues.
  _GCHAT_SERVICE_NAME = "google_chat"
  _GCHAT_HTTP_METHOD = "POST"
  _URL_PARAM_NAME = "webhook_url"
  _FORMAT_PARAM_NAME = "msg_format"

  def __init__(self):
    super(GchatHandler, self).__init__(
        self._GCHAT_SERVICE_NAME, self._GCHAT_HTTP_METHOD
    )

  def CheckConfigParams(self, config_params: Dict[Text, Any]):
    """Checks if the given config params is a valid one that has all the necessary configs.

    The google chat handler needs the webhook url of a google chat room and the
    format setting to forward the notifications.
    """
    self.CheckServiceNameInConfigParams(config_params)

    # The google chat room webhook url is needed to send the requests.
    if not (
        self._URL_PARAM_NAME in config_params
        and isinstance(config_params[self._URL_PARAM_NAME], str)
    ):
      raise ConfigParamsError(
          f"{self._URL_PARAM_NAME} is not set or not a string: {config_params}"
      )

    if not (
        self._FORMAT_PARAM_NAME in config_params
        and config_params[self._FORMAT_PARAM_NAME] in self._SUPPORTED_FORMAT
    ):
      raise ConfigParamsError(
          f"{self._FORMAT_PARAM_NAME} is not set or not a valid option:"
          f" {config_params}"
      )

  def _GetHttpUrl(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Text:
    return config_params[self._URL_PARAM_NAME]

  def _BuildHttpRequestHeaders(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Dict[Text, Any]:
    http_headers = {"Content-Type": "application/json; charset=UTF-8"}
    return http_headers

  def _BuildHttpRequestBody(
      self, config_params: Dict[Text, Any], notification: Dict[Any, Any]
  ) -> Text:
    msg_format = config_params["msg_format"]
    """Converts the notification into a http request body."""
    if msg_format == "text":
      message_body = {"text": json.dumps(notification)}
      return json.dumps(message_body)

    assert msg_format == "card"
    try:
      started_time = notification["incident"].get("started_at")
      if started_time:
        started_time = datetime.datetime.utcfromtimestamp(int(started_time))
        started_time_str = started_time.strftime("%Y-%m-%d %H:%M:%S (UTC)")
      else:
        started_time_str = ""

      incident_display_name = notification["incident"]["condition"][
          "displayName"
      ]
      incident_resource_labels = notification["incident"]["resource"]["labels"]
      incident_url = notification["incident"]["url"]
      incident_state = notification["incident"]["state"]
      header_color = self._CLOSED_ISSUE_HEADER_COLOR
      if incident_state == "open":
        header_color = self._OPEN_ISSUE_HEADER_COLOR

      incident_ended_at = notification["incident"].get("ended_at")
      if incident_ended_at:
        incident_ended_at = datetime.datetime.utcfromtimestamp(
            int(incident_ended_at)
        )
      else:
        incident_ended_at = ""
      incident_summary = notification["incident"]["summary"]
    except:
      logging.error("failed to get notification fields %s", notification)
      raise

    # Set the alert severity level if it is set in the user labels.
    try:
      incident_severity = notification["incident"]["policy_user_labels"][
          "severity"
      ]
      incident_severity_display_str = (
          f', <br><b><font color="{header_color}">Severity:</font></b>'
          f" {incident_severity}"
      )
    except:
      logging.error(
          f"Failed to extract the severity level info : {notification}"
      )
      incident_severity_display_str = ""

    message_body = {
        "cards": [{
            "sections": [{
                "widgets": [
                    {
                        "textParagraph": {
                            "text": (
                                "<b><font"
                                ' color="{header_color}">Summary:</font></b>'
                                f" {incident_summary}, <br><b><font"
                                f' color="{header_color}">State:</font></b>'
                                f" {incident_state}{incident_severity_display_str}"
                            )
                        }
                    },
                    {
                        "textParagraph": {
                            "text": (
                                "<b>Condition Display Name:</b>"
                                f" {incident_display_name} <br><b>Start at:</b>"
                                f" {started_time_str}<br><b>Incident"
                                f" Labels:</b> {incident_resource_labels}"
                            )
                        }
                    },
                    {
                        "buttons": [{
                            "textButton": {
                                "text": "View Incident Details",
                                "onClick": {
                                    "openLink": {"url": f"{incident_url}"}
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
      logging.error("Failed to send the notification: %s", err)
      return str(err), 400
    except BaseException as err:
      logging.error("Failed to send the notification: %s", err)
      return str(err), 500

    try:
      logging.info("Sending the notification: %s", notification)
      # content is of type bytes.
      http_response, content = self._SendHttpRequest(
          config_params, notification
      )
      logging.info("Successfully sent the notification: %s", http_response)
    except BaseException as err:
      logging.error("Failed to send the notification: %s", err)
      return str(err), 500
    return content, http_response.status


class MSTeamsHandler(HttpRequestBasedHandler):
  """Handler that integrates the Google alerting pubsub channel with the Microsoft Teams service.

  It converts a received notification into a well-formatted Microsoft Teams
  message and sends it to the configured Microsoft Teams channel. The config
  parameter it needs is the Microsoft Teams channel webhook URL.
  """

  # The handler supports microsoft teams text and card formats,
  # see https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and
  # -connectors/how-to/connectors-using?tabs=cURL%2Ctext1#send-messages-using-curl-and-powershell
  # and https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and
  # -connectors/how-to/add-incoming-webhook?tabs=newteams%2Cdotnet#format-the-message
  _SUPPORTED_FORMAT = {"text", "card"}
  _TEAMS_SERVICE_NAME = "microsoft_teams"
  _TEAMS_HTTP_METHOD = "POST"
  _URL_PARAM_NAME = "webhook_url"
  _FORMAT_PARAM_NAME = "msg_format"

  def __init__(self):
    super().__init__(self._TEAMS_SERVICE_NAME, self._TEAMS_HTTP_METHOD)

  def CheckConfigParams(self, config_params: Dict[str, Any]):
    """Checks if the given config params is a valid one that has all the necessary configs.

    The Microsoft Teams handler needs the webhook url of a Microsoft Teams
    channel and the format setting to forward the notifications.

    Args:
        config_params: A dictionary that includes information about where/how to
          send notifications to a 3rd-party service.

    Raises:
        ConfigParamsError: If config parameters are invalid.
    """
    self.CheckServiceNameInConfigParams(config_params)

    # The Microsoft Teams channel webhook url is needed to send the requests.
    if not (
        self._URL_PARAM_NAME in config_params
        and isinstance(config_params[self._URL_PARAM_NAME], str)
    ):
      raise ConfigParamsError(
          f"{self._URL_PARAM_NAME} is not set or not a string: {config_params}"
      )

    if not (
        self._FORMAT_PARAM_NAME in config_params
        and config_params[self._FORMAT_PARAM_NAME] in self._SUPPORTED_FORMAT
    ):
      raise ConfigParamsError(
          f"{self._FORMAT_PARAM_NAME} is not set or not a valid option:"
          f" {config_params}"
      )

  def _GetHttpUrl(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> str:
    return config_params[self._URL_PARAM_NAME]

  def _BuildHttpRequestHeaders(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> Dict[str, Any]:
    http_headers = {"Content-Type": "application/json; charset=UTF-8"}
    return http_headers

  def _GetAllLabels(self, incident: Dict[str, Any]) -> Dict[str, str]:
    """Gets all resource, metric, and metadata labels from the incident."""
    resource_labels = incident.get("resource", {}).get("labels", {})
    metric_labels = incident.get("metric", {}).get("labels", {})
    metadata_system_labels = incident.get("metadata", {}).get(
        "system_labels", {}
    )
    metadata_user_labels = incident.get("metadata", {}).get("user_labels", {})

    all_labels = {}
    all_labels.update(resource_labels)
    all_labels.update(metric_labels)
    all_labels.update(metadata_system_labels)
    all_labels.update(metadata_user_labels)

    return all_labels

  def _BuildHttpRequestBody(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> str:
    msg_format = config_params.get("msg_format", "text")

    if msg_format == "text":
      message_body = {"text": json.dumps(notification)}
      return json.dumps(message_body)

    assert msg_format == "card"
    try:
      incident = notification.get("incident", {})
      quick_links = incident.get("documentation", {}).get("links", "N/A")
      incident_url = incident.get("url", "N/A")
      incident_state = incident.get("state", "N/A")
      policy_name = incident.get("policy_name", "N/A")
      severity = incident.get("severity", "N/A")
      documentation = incident.get("documentation", {}).get("content", "N/A")
      metric_type = incident.get("metric", {}).get("type", "N/A").split("/")[-1]

      # Extract all relevant labels, including resource, metric, and metadata
      # labels
      all_labels = self._GetAllLabels(incident)

    except Exception as e:
      logging.error("Failed to get notification fields %s", notification)
      raise e

    # Determine the color based on the incident state
    state_color = "Attention" if incident_state == "open" else "Green"
    state_image = (
        "https://ssl.gstatic.com/cloud-monitoring/incident_open.png"
        if incident_state == "open"
        else "https://ssl.gstatic.com/cloud-monitoring/incident_closed.png"
    )
    severity_images = {
        "Critical": (
            "https://ssl.gstatic.com/cloud-monitoring/severity_critical.png"
        ),
        "Error": "https://ssl.gstatic.com/cloud-monitoring/severity_error.png",
        "Warning": (
            "https://ssl.gstatic.com/cloud-monitoring/severity_warning.png"
        ),
        "No severity": (
            "https://ssl.gstatic.com/cloud-monitoring/severity_null.png"
        ),
    }

    severity_image = severity_images.get(
        severity,
        "https://ssl.gstatic.com/cloud-monitoring/severity_null.png",
    )

    # Construct quick links string if there are quick links
    quick_links_string = ""
    if quick_links != "N/A":
      links_list = [
          f"[{link['DisplayName']}]({link['URL']})" for link in quick_links
      ]
      quick_links_string = "**Quick links:** " + " • ".join(links_list)

    # Construct FactSet from all gathered labels and include metric_type
    fact_set = [
        {"title": key, "value": value} for key, value in all_labels.items()
    ]
    fact_set.append({"title": "metric_type", "value": metric_type})
    fact_set = sorted(fact_set, key=lambda x: x["title"])

    # Construct the adaptive card body
    card_body = [
        {
            "type": "Container",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "{{policy_name}}",
                    "weight": "Bolder",
                    "size": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": "{{summary}}",
                    "isSubtle": True,
                    "wrap": True,
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [{
                                "type": "Image",
                                "url": "{{state_image}}",
                                "width": "18px",
                                "height": "18px",
                                "spacing": "None",
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [{
                                "type": "TextBlock",
                                "text": "{{state}}",
                                "color": "{{state_color}}",
                                "size": "Small",
                                "spacing": "None",
                                "wrap": True,
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [{
                                "type": "Image",
                                "url": "{{severity_image}}",
                                "width": "18px",
                                "height": "18px",
                                "spacing": "None",
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [{
                                "type": "TextBlock",
                                "text": "{{severity}}",
                                "size": "Small",
                                "weight": "Default",
                                "spacing": "Small",
                                "wrap": True,
                            }],
                        },
                    ],
                },
            ],
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View alert",
                    "url": "{{url}}",
                    "isPrimary": True,
                },
                {
                    "type": "Action.ShowCard",
                    "title": "Additional details",
                    "card": {
                        "type": "AdaptiveCard",
                        "body": [{
                            "type": "Container",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Additional details",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": quick_links_string,
                                    "wrap": True,
                                    "separator": (
                                        True if quick_links_string else False
                                    ),
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Labels",
                                    "size": "Small",
                                    "weight": "Bolder",
                                    "spacing": "Large",
                                },
                                {
                                    "type": "FactSet",
                                    "facts": fact_set,
                                    "spacing": "Small",
                                },
                            ],
                        }],
                    },
                },
            ],
        },
    ]

    # Add documentation section if not empty
    if documentation.strip() and documentation != "N/A":
      card_body[1]["actions"][1]["card"]["body"][0]["items"].extend([
          {
              "type": "TextBlock",
              "text": "Documentation",
              "size": "Small",
              "weight": "Bolder",
              "spacing": "Large",
          },
          {
              "type": "TextBlock",
              "text": "{{documentation}}",
              "spacing": "Small",
              "wrap": True,
          },
      ])

    adaptive_card_template = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "type": "AdaptiveCard",
                "body": card_body,
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.5",
            },
        }],
    }

    # Replace placeholders with actual data
    message_body = (
        json.dumps(adaptive_card_template)
        .replace("{{policy_name}}", policy_name)
        .replace("{{summary}}", incident.get("summary", "N/A"))
        .replace("{{state_image}}", state_image)
        .replace("{{state}}", incident_state)
        .replace("{{state_color}}", state_color)
        .replace("{{severity_image}}", severity_image)
        .replace("{{severity}}", severity)
        .replace("{{url}}", incident_url)
        .replace("{{documentation}}", documentation)
    )

    return message_body

  def SendNotification(
      self, config_params: Dict[str, Any], notification: Dict[Any, Any]
  ) -> Tuple[str, int]:
    """Sends a notification to a Microsoft Teams Channel."""
    try:
      self.CheckConfigParams(config_params)
    except ConfigParamsError as err:
      logging.error("Failed to send the notification: %s", err)
      return str(err), 400
    except Exception as err:  # pylint: disable=broad-except
      logging.error("Failed to send the notification: %s", err)
      return str(err), 500

    try:
      logging.info("Sending the notification: %s", notification)
      # content is of type bytes.
      http_response, content = self._SendHttpRequest(
          config_params, notification
      )
      logging.info("Successfully sent the notification: %s", http_response)
    except Exception as err:  # pylint: disable=broad-except
      logging.error("Failed to send the notification: %s", err)
      return str(err), 500
    return content, http_response.status
