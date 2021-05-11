# Copyright 2020 Google, LLC.
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

"""Module to re-format Pub/Sub notifications to an easier to read format.

This module defines functions and errors to handle input from Google Monitoring,
such as Pub/Sub notifications.
"""
import json
class Error(Exception):
    """Base class for all errors raised in this module."""

def check_data(data):
    if data is None:
        return ''
    else:
        return data

def parse_notification(notification, format='text'):
    """Converts the input message into a JSON object in the given format."""
    if format not in ['text', 'cards']:
        raise Error('Pubsub messages can only be parsed into two formats : "text" and "cards"!')

    if format == 'text':
        bot_message = {'text': json.dumps(notification)}
        return bot_message

    try:
        incident_id = notification['incident']['incident_id']
        started_time = notification['incident']['started_at']
        policy_name = notification['incident']['policy_name']
        incident_url = notification['incident']['url']
        incident_state = notification['incident']['state']
        incident_ended_at = notification['incident']['ended_at']
        incident_summary = notification['incident']['summary']       
    except:
        print("failed to get notification fields %s" % notification)
        raise 
 
    raw_msg = {
        "cards": [
            {
                "header": {
                    "title": "Incident ID: {}".format(incident_id),
                    "subtitle": "Alerting Policys: {}".format(policy_name),
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "<b>Start at:</b> {}, <b>Current State:</b> {}, <b>End at:</b> {}, <b>Summary:</b> {} ".format(started_time, incident_state, incident_ended_at, incident_summary)
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
    return raw_msg