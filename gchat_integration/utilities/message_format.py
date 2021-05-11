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

def parse_message(pubsub_message):
    incident_id = pubsub_message['incident']['incident_id']
    resource_id = pubsub_message['incident']['resource_id']
    resource_name = pubsub_message['incident']['resource_name']
    resource_type = pubsub_message['incident']['resource']['type']
    labels_instance_id = pubsub_message['incident']['resource']['labels']['instance_id']
    labels_project_id = pubsub_message['incident']['resource']['labels']['project_id']
    labels_zone = pubsub_message['incident']['resource']['labels']['zone']
    resource_display_name = pubsub_message['incident']['resource_display_name']
    resource_type_display_name = pubsub_message['incident']['resource_type_display_name']
    metric_type = pubsub_message['incident']['metric']['type']
    metric_displayName = pubsub_message['incident']['metric']['displayName']
    started_time = pubsub_message['incident']['started_at']
    policy_name = pubsub_message['incident']['policy_name']
    condition_name = pubsub_message['incident']['condition_name']
    name_condition = pubsub_message['incident']['condition']['name']
    condition_displayName = pubsub_message['incident']['condition']['displayName']
    condition_filter = pubsub_message['incident']['condition']['conditionThreshold']['filter']
    condition_aggregrations = pubsub_message['incident']['condition']['conditionThreshold']['aggregations'][0]['alignmentPeriod']
    condition_perSeriesAligner = pubsub_message['incident']['condition']['conditionThreshold']['aggregations'][0]['perSeriesAligner']
    condition_comparison = pubsub_message['incident']['condition']['conditionThreshold']['comparison']
    condition_duration = pubsub_message['incident']['condition']['conditionThreshold']['duration']
    condition_trigger_count = pubsub_message['incident']['condition']['conditionThreshold']['trigger']
    incident_url = pubsub_message['incident']['url']
    incident_state = pubsub_message['incident']['state']
    incident_ended_at = pubsub_message['incident']['ended_at']
    incident_summary = pubsub_message['incident']['summary']

    formatted_message = ('incident_id: ' + incident_id + '\n'
        'resource_id: ' + resource_id + '\n'
        'resource_name: ' + resource_name + '\n'
        'resource: ' + '\n'
        '\ttype: ' + resource_type + '\n'
        '\tlabels: ' + '\n'
        '\t\tinstance_id: ' + labels_instance_id + '\n'
        '\t\tproject_id: ' + labels_project_id + '\n'
        '\t\tzone: ' + labels_zone + '\n'
        'resource_display_name: ' + resource_display_name + '\n'
        'resource_type_display_name: ' + resource_type_display_name + '\n'
        'metric: ' + '\n'
        '\ttype: ' + metric_type + '\n'
        '\tdisplayName: ' + metric_displayName + '\n'
        'started_at: ' + str(started_time) + '\n'
        'policy_name: ' + policy_name + '\n'
        'condition_name: ' + condition_name + '\n'
        'condition:' + '\n'
        '\tname: ' + name_condition + '\n'
        '\tdisplayName: ' + condition_displayName + '\n'
        '\tconditionThreshold: ' + '\n'
        '\t\tfilter: ' + condition_filter + '\n'
        '\t\taggregrations: ' + '\n'
        '\t\t\talignmentPeriod: ' + condition_aggregrations + '\n'
        '\t\t\tperSeriesAligner: ' + condition_perSeriesAligner + '\n'
        '\t\tcomparison: ' + condition_comparison + '\n'
        '\t\tduration: ' + condition_duration + '\n'
        '\t\ttrigger: ' + '\n'
        '\t\t\tcount: ' + str(condition_trigger_count) + '\n'
        'url: ' + incident_url + '\n'
        'state: ' + incident_state + '\n'
        'ended_at: ' + incident_ended_at + '\n'
        'summary: ' + incident_summary + '\n')

    raw_msg = {
        "cards": [
            {
                "sections": [
                    {
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "<b>Roses</b> are <font color=\"#ff0000\">red</font>,<br><i>Violets</i> are <font color=\"#0000ff\">blue</font>"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    } 
    formatted_message = json.dumps(raw_msg)
    return formatted_message
