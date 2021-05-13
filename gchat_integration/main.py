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
from google.cloud import storage
from utilities import pubsub, message_format

app_config = config.load()
logging.basicConfig(level=app_config.LOGGING_LEVEL)

# logger inherits the logging level and handlers of the root logger
logger = logging.getLogger(__name__)

def load_channel_name_to_url_map(bucket_name):
    url = 'https://chat.googleapis.com/v1/spaces/AAAAHgCPlz4/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=ILvfE5si4Pdab8iVtxnZK3_QcPIJpB55XdhGjYZg9i0%3D'
    json_file = {
        "wdzc_policy_ch": url,
    }
    storage_client = storage.Client()
    # Set our bucket 
    bucket = storage_client.get_bucket(bucket_name)  
    blob = bucket.blob('channel_name_to_url_map.json')
    blob.upload_from_string(
        data=json.dumps(json_file),
        content_type='application/json'
    )
 
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.get_blob('channel_name_to_url_map.json')
    fileData = json.loads(blob.download_as_string())
    logging.info("the gcs json object is : %s", fileData)

url_map = load_channel_name_to_url_map('url_config')

app = Flask(__name__)
app.config.from_object(app_config)
# [END run_pubsub_server_setup]


# [START run_pubsub_handler]
@app.route('/', methods=['POST'])
def handle_pubsub_message():
    pubsub_received_message = request.get_json()

    # parse the Pub/Sub data
    try:
        pubsub_data_string = pubsub.parse_data_from_message(pubsub_received_message)
    except pubsub.DataParseError as e:
        logger.error(e)
        return (str(e), 400)

    # load the notification from the data
    try:
        monitoring_notification_dict = json.loads(pubsub_data_string)
    except json.JSONDecodeError as e:
        logger.error(e)
        return (f'Notification could not be decoded due to the following exception: {e}', 400)

    return send_monitoring_notification_to_third_party(monitoring_notification_dict)
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
    url = url_map['wdzc_policy_ch']
    messages_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    bot_message = message_format.parse_notification(notification, format='cards')

    http_obj = Http()

    try:
        response = http_obj.request(
            uri = url,
            method = 'POST',
            headers = messages_headers,
            body = json.dumps(bot_message),
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