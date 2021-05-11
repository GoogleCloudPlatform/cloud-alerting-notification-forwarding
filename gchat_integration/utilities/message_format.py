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

    formatted_message = {
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
    
    return formatted_message
