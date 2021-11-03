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

"""Module that provides handlers to integrate with 3rd-party services."""

import abc
import datetime
import json
import logging

from httplib2 import Http
from typing import Any, Dict, Text
from google.cloud import storage
from utilities import config_server

class Error(Exception):
    """Base error for this module."""
    pass

class ConfigParamError(Error):
    """The config parameters used to create a handler are invalid."""
    pass

class ServiceHandler(abc.ABC):
    """Abstract base class that represents a 3rd-party service handler."""

    def __init__(self, service_name: Text):
        # service_name is the name of the service this handler is to integrate with.
        self._service_name = service_name

    def CheckServiceNameInConfigParam(self, config_param: Dict[str, Any])-> bool:
        """Ensures 'service_name' is in the config_param and set correctly. """        
        if not ('service_name' in config_param and config_param['service_name'] == self._service_name):
            raise ConfigParamError('service_name is not set or different from {} : {}', format(
                self._service_name, config_param))

    @abc.abstractmethod
    def CheckConfigParam(self, config_param: Dict[str, Any]):
        """Checks if the given config param is a valid one that has all the necessary configs."""
        pass

    @abc.abstractmethod
    def _BuildMessageBody(self, notification: Dict[str, Any], format: Text) -> Text:
        """Converts the notification into a message body to be included in the request.
        
        Args:
           notification: An incoming alerting message to forward. See the comments below for more details.
           format: The format to use.

        Returns:
           A json dump (str) of the created message json object.

        Raises:
            Any exception raised when sending the notificaton.  
        """

    @abc.abstractmethod
    def SendNotification(self, config_param: Dict[str, Any], notification: Dict[Any, Any]):
        """Sends a notification to a given service endpoint.

        It uses the config_param to get the information about where/how to send notifications to a 3rd-party service,
        converts the received message, which is a dictionary containing a json object defined at
        https://cloud.google.com/monitoring/support/notification-options (see Schema structure), into api call/http request, and sends the requests to the service endpoint.

        Args:
           config_param: A dictionary that includes information about where/how to send notifications to a 3rd-party service.
           notification: An incoming alerting message to forward.

        Raises:
            Any exception raised when sending the notificaton.  
        """
        pass

class GchatHandler(ServiceHandler):
    """Handler that integrates the Google alerting pubsub chananel with the Google Chat service.

    It converts a received notification into a well-formated Google Chat message and sends it to the 
    configed Google Chat room. The config parameter its needs is the Google chat room webhook URL.   
    """

    # The handler supports two formats: text and card, see https://developers.google.com/chat/api/guides/message-formats/basic and https://developers.google.com/chat/api/guides/message-formats/cards and 
    _SUPPORTED_FORMAT = set(['text', 'card'])
    _RED_COLOR = '#FF0000'  # Red for open issues.
    _BLUE_COLOR = '#0000FF'  # Blue for closed issues.

    def __init__(self):
        super(GchatHandler, self).__init__('google_chat')

    def CheckConfigParam(self, config_param: Dict[str, Any]):
        """Checks if the given config param is a valid one that has all the necessary configs.
        
        The google chat handler  needs the webhook url of a google chat room and the format setting to forward the notifications.
        """
        self.CheckServiceNameInConfigParam(config_param)
        
        # The google chat room webhook url is needed to send the requests.
        if not ('webhook_url' in config_param and isinstance(config_param['webhook_url'], str)):
            raise ConfigParamError('webhook_url is not set or not a string: {}', format(
                config_param))

        if not ('msg_format' in config_param and config_param in self._SUPPORTED_FORMAT):
            raise ConfigParamError('msg_format is not set or not a valid option: {}', format(
                config_param))
                       
    def _BuildMessageBody(self, notification: Dict[str, Any], format: Text) -> Text:
        """Converts the notification into a message body to be included in the request."""
        if format == 'text':
            message_body = {'text': json.dumps(notification)}
            return json.dumps(message_body)

        assert(format == 'card')
        try:
            started_time = notification['incident']['started_at']
            if started_time:
                started_time = datetime.datetime.utcfromtimestamp(int(started_time))
                started_time_str = started_time.strftime("%Y-%m-%d %H:%M:%S (UTC)") 
            else:
                started_time_str = ''
        
            incident_display_name = notification['incident']['condition']['displayName']
            incident_resource_labels = notification['incident']['resource']['labels']
            incident_url = notification['incident']['url']
            incident_state = notification['incident']['state']
            header_color = self._BLUE_COLOR
            if incident_state == 'open':
                header_color = self._RED_COLOR

            incident_ended_at = notification['incident']['ended_at']
            if incident_ended_at:
                incident_ended_at = datetime.datetime.utcfromtimestamp(int(incident_ended_at))
            incident_summary = notification['incident']['summary']       
        except:
            print("failed to get notification fields %s" % notification)
            raise 
 
        message_body = {
            "cards": [
                {
                    "sections": [
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": "<b><font color=\"{color}\">Summary:</font></b> {}, <br><b><font    color=\"{color}\">State:</font></b> {}".format(incident_summary, incident_state, color=header_color)
                                    }
                                },
                                {
                                    "textParagraph": {
                                        "text": "<b>Condition Display Name:</b> {} <br><b>Start at:</b> {}<br><b>Incident Labels:</b> {}".format(incident_display_name, started_time_str, incident_resource_labels)
                                    }
                                },
                                {
                                    "buttons": [
                                        {
                                            "textButton": {
                                                "text": "View Incident Details",
                                                "onClick": {
                                                    "openLink": {
                                                        "url": "{}".format(incident_url)
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        } 
        return json.dumps(message_body)

    def SendNotification(self, config_param: Dict[str, Any], notification: Dict[Any, Any]):
        """Sends a notification to a Google chat room."""

        self.CheckConfigParam(config_param)

        url = config_param['webhook_url']
        messages_headers = {'Content-Type': 'application/json; charset=UTF-8'}

        message_body = self._BuildMessageBody(notification, format=config_param['msg_format'])

        http_obj = Http()

        try:
            response = http_obj.request(
                uri = url,
                method = 'POST',
                headers = messages_headers,
                body = message_body,
            )
            logging.info(response)
        except Exception as e:
            return(str(e), 400)
        return(notification, 200)