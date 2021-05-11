# Copyright 2019 Google, LLC.
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

# The code in this module is based on
# https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/run/pubsub/main.py.
# See https://cloud.google.com/run/docs/tutorials/pubsub for the accompanying
# Cloud Run/PubSub solutions guide.

"""Runs Cloud Monitoring Notification Integration app with Flask."""

# [START run_pubsub_server_setup]
import logging
import os
import json

from flask import Flask, request

import config
from httplib2 import Http
from utilities import pubsub, message_format


app_config = config.load()
logging.basicConfig(level=app_config.LOGGING_LEVEL)

# logger inherits the logging level and handlers of the root logger
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(app_config)
# [END run_pubsub_server_setup]


# [START run_pubsub_handler]
@app.route('/', methods=['POST'])
def handle_pubsub_message():
    pubsub_received_message = request.get_json()
    pubsub_received_message = json.dumps(pubsub_received_message).replace('None', '""')
    pubsub_received_message = json.loads(pubsub_received_message)

    # parse the Pub/Sub data
    try:
        pubsub_data_string = pubsub.parse_data_from_message(pubsub_received_message)
    except pubsub.DataParseError as e:
        logger.error(e)
        return (str(e), 400)

    return send_monitoring_notification_to_third_party(pubsub_data_string)
# [END run_pubsub_handler]


def send_monitoring_notification_to_third_party(notification):
    """Send a given monitoring notification to a third party service.

    Args:
        notification: A dictionary with the parsed out pubsub notificaiton message.

    Returns:
        A tuple containing an HTTP response message and HTTP status code
        indicating whether or not sending the notification to the third
        party service was successful.
    """

    # url is the Incoming webhooks url for a gchat room
    
    url = 'https://chat.googleapis.com/v1/spaces/AAAAHgCPlz4/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=ILvfE5si4Pdab8iVtxnZK3_QcPIJpB55XdhGjYZg9i0%3D'
    messages_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    # notification = message_format.parse_message(notification)
    bot_message = {'text': notification}

    http_obj = Http()

    try:
        response = http_obj.request(
            uri = url,
            method = 'POST',
            headers = messages_headers,
            body = json.dumps(bot_message, indent=4),
        )
        print(response)
    except Exception as e:
        return(str(e), 400)
    return(notification, 200)

if __name__ == '__main__':
    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080
    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host='127.0.0.1', port=PORT, debug=True)