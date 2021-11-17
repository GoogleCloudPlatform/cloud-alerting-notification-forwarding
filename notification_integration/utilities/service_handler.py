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
from typing import Any, Dict, Text, Tuple
from google.cloud import storage
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

    def CheckServiceNameInConfigParams(self, config_params: Dict[str, Any])-> bool:
        """Ensures 'service_name' is in the config_params and set correctly. """        
        if not ('service_name' in config_params and config_params['service_name'] == self._service_name):
            raise ConfigParamsError(f'service_name is not set or different from {self._service_name} : {config_params}')

    @abc.abstractmethod
    def CheckConfigParams(self, config_params: Dict[str, Any]):
        """Checks if the given config params is a valid one that has all the necessary configs."""
        pass

    @abc.abstractmethod
    def SendNotification(self, config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Tuple[Text, int]:
        """Sends a notification to a 3rd-party service endpoint.

        It uses the config_params to get the information about where/how to send notifications to a 3rd-party service,
        converts the received message, which is a dictionary containing a json object defined at
        https://cloud.google.com/monitoring/support/notification-options (see Schema structure), into api call/http request, and sends the requests to the service endpoint.

        Args:
           config_params: A dictionary that includes information about where/how to send notifications to a 3rd-party service.
           notification: An incoming alerting message to forward.

        Returns:
           A tuple (response_msg, status_code), where response_msg is the response message string and status_code is the status code to be returned.

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
    def _BuildHttpRequestBody(self, config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Text:
        """Converts the notification into a http request body.
        
        Args:
            config_params: A dictionary that includes information about where/how to send notifications to a 3rd-party service.
            notification: An incoming alerting message to forward.

        Returns:
            A json dump (str) of the created message json object.

        Raises:
            Any exception raised during the process.  
        """
        pass

    @abc.abstractmethod
    def _BuildHttpRequestHeaders(self, config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Dict[Text, Any]:
        """Builds the Http request headers.
        
        Args:
            config_params: A dictionary that includes information about where/how to send notifications to a 3rd-party service.
            notification: An incoming alerting message to forward.

        Returns:
            A http request headers to be included in the outgoing http request.

        Raises:
            Any exception raised during the process.  
        """
        pass

    @abc.abstractmethod
    def _GetHttpUrl(self,  config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Text:
        """Gets the Http URL from the configuration parameters.
        
        Args:
            config_params: A dictionary that includes information about where/how to send notifications to a 3rd-party service.
            notification: An incoming alerting message to forward.

        Returns:
           A http URL used to sent the http request.

        Raises:
            Any exception raised during the process.  
        """
        pass

    def SendNotification(self, config_params: Dict[str, Any], notification: Dict[Any, Any]):
        """Sends a notification to a 3rd-party service via a http request."""
        http_url = self._GetHttpUrl(config_params, notification)
        messages_headers = self._BuildHttpRequestHeaders(config_params, notification)
        message_body = self._BuildHttpRequestBody(config_params, notification)

        http_obj = Http()

        response = http_obj.request(
            uri = http_url,
            method = self._http_method,
            headers = messages_headers,
            body = message_body,
        )
        logging.info(response)
        return (str(notification) ,200)    

    
class GchatHandler(HttpRequestBasedHandler):
    """Handler that integrates the Google alerting pubsub chananel with the Google Chat service.

    It converts a received notification into a well-formated Google Chat message and sends it to the 
    configed Google Chat room. The config parameter its needs is the Google chat room webhook URL.   
    """

    # The handler supports two formats: text and card, see https://developers.google.com/chat/api/guides/message-formats/basic and https://developers.google.com/chat/api/guides/message-formats/cards and 
    _SUPPORTED_FORMAT = set(['text', 'card'])
    _RED_COLOR = '#FF0000'  # Red for open issues.
    _BLUE_COLOR = '#0000FF'  # Blue for closed issues.

    def __init__(self):
        super(GchatHandler, self).__init__('google_chat', 'POST')

    def CheckConfigParams(self, config_params: Dict[str, Any]):
        """Checks if the given config params is a valid one that has all the necessary configs.
        
        The google chat handler  needs the webhook url of a google chat room and the format setting to forward the notifications.
        """
        self.CheckServiceNameInConfigParams(config_params)
        
        # The google chat room webhook url is needed to send the requests.
        if not ('webhook_url' in config_params and isinstance(config_params['webhook_url'], str)):
            raise ConfigParamsError('webhook_url is not set or not a string: {}'.format(
                config_params))

        if not ('msg_format' in config_params and config_params['msg_format'] in self._SUPPORTED_FORMAT):
            raise ConfigParamsError('msg_format is not set or not a valid option: {}'.format(
                config_params))
                       
    def _GetHttpUrl(self,  config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Text:
        return config_params['webhook_url']

    def _BuildHttpRequestHeaders(self, config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Dict[Text, Any]:
        http_headers = {'Content-Type': 'application/json; charset=UTF-8'}
        return http_headers

    def _BuildHttpRequestBody(self, config_params: Dict[str, Any], notification: Dict[Any, Any]) -> Text:
        format = config_params['msg_format']
        """Converts the notification into a http request body."""
        if format == 'text':
            message_body = {'text': json.dumps(notification)}
            return json.dumps(message_body)

        assert(format == 'card')
        try:
            started_time = notification['incident']['started_at']
            if started_time:
                started_time = datetime.datetime.utcfromtimestamp(int(started_time))
                started_time_str = started_time.strftime('%Y-%m-%d %H:%M:%S (UTC)') 
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
            logging.error('failed to get notification fields %s'.format(notification))
            raise 

        # Set the alert severity level if it is set in the user labels.
        try:
            incident_severity = notification['incident']['policy_user_labels']['severity']
            incident_severity_display_str = ', <br><b><font    color="{color}">Severity:</font></b> {severity}'.format(severity=incident_severity, color=header_color)
        except:
            logging.error('Failed to extract the severity level info : {}'.format(notification))
            incident_severity_display_str = ''

        message_body = {
            'cards': [
                {
                    'sections': [
                        {
                            'widgets': [
                                {
                                    'textParagraph': {
                                        'text': '<b><font color="{color}">Summary:</font></b> {}, <br><b><font    color="{color}">State:</font></b> {}{}'.format(incident_summary, incident_state, incident_severity_display_str, color=header_color)
                                    }
                                },
                                {
                                    'textParagraph': {
                                        'text': '<b>Condition Display Name:</b> {} <br><b>Start at:</b> {}<br><b>Incident Labels:</b> {}'.format(incident_display_name, started_time_str, incident_resource_labels)
                                    }
                                },
                                {
                                    'buttons': [
                                        {
                                            'textButton': {
                                                'text': 'View Incident Details',
                                                'onClick': {
                                                    'openLink': {
                                                        'url': '{}'.format(incident_url)
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

    def SendNotification(self, config_params: Dict[str, Any], notification: Dict[Any, Any]):
        """Sends a notification to a Google chat room."""
        try:
            self.CheckConfigParams(config_params)
        except ConfigParamsError as e:
            logging.error(f'Failed to send the notification: {e}')
            return (str(e), 400)
        except BaseException as e:
            logging.error(f'Failed to send the notification: {e}')
            return (str(e), 500)

        try:
            http_response = super(GchatHandler, self).SendNotification(config_params, notification)
            logging.info(f'Successfully sent the notification: {http_response}')
        except BaseException as e:
            logging.error(f'Failed to send the notification: {e}')
            return (str(e), 400)


