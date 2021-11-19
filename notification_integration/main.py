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

# The code in this module is based on
# https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/run/pubsub/main.py.
# See https://cloud.google.com/run/docs/tutorials/pubsub for the accompanying
# Cloud Run/PubSub solutions guide.

"""Runs Cloud Alerting Notification Integration app with Flask."""

import logging
import os
import json

from flask import Flask, request

from httplib2 import Http

from utilities import config_server, pubsub, service_handler

# logger inherits the logging level and handlers of the root logger
logger = logging.getLogger(__name__)

# The keys of the config_map corresponds to the local pubsub topic
# variables in main.tf.
config_map = {
    'tf-topic-cpu': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': 'https://chat.googleapis.com/v1/spaces/AAAAjOjX3I0/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=e9mcRhsfwYw51zvyTJ5ckw7YVC8ViR8bl7dtP8UrJGY%3D'},
    'tf-topic-disk': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': 'https://chat.googleapis.com/v1/spaces/AAAA9xJV6L8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=cgLW9UExTH8kipz2cBOaj51LOa4d2OJmdsXJkX8-Fas%3D'}
}
config_params_server = config_server.InMemoryConfigServer(config_map)
gchat_handler = service_handler.GchatHandler()
service_names_to_handlers = {
    'google_chat': gchat_handler,
}

app = Flask(__name__)


@app.route('/<config_id>', methods=['POST'])
def handle_pubsub_message(config_id):
    try:
        config_param = config_params_server.GetConfig(config_id)
    except BaseException as e:
        err_msg = 'Failed to get config parameters for {}: {}'.format(config_id, e)
        logging.error(err_msg)
        return(err_msg, 500)
    if 'service_name' not in config_param:
        err_msg = '"service_name" not found in the config parameters: {}'.format(config_id)
        logging.error(err_msg)
        return(err_msg, 500)
    if config_param['service_name'] not in service_names_to_handlers:
        err_msg = 'No handler found for the service {}'.format(config_param['service_name'])
        logging.error(err_msg)
        return(err_msg, 500)

    handler = service_names_to_handlers[config_param['service_name']]
    
    # Parse the Pub/Sub raw message to get the notification
    pubsub_received_message = request.get_json()
    try:
        notification = pubsub.ExtractNotificationFromPubSubMsg(pubsub_received_message)
        return handler.SendNotification(config_param, notification)
    except pubsub.DataParseError as e:
        logger.error(f'Pubsub message parse error: {e}')
        return (str(e), 400)
    except BaseException as e:
        logger.error(f'Unexpected error when processing Pubsub message: {e}')
        return (str(e), 400)

def main():
    # By default, we use the in-memory config server created in the above code.
    # If the env. variable 'USE_GCS_CONFIG_SERVER' is set to 'True', we will use
    # a GCS config server. The GCS bucket name is gcs_config_bucket_{PROJECT_ID} and the
    # config file/object name is gcs_config_file.json.
    # If you want to use the GCS config file, don't forget to manually create the GCS
    # bucket and upload the config file to the bucket before running the deployment 
    # script.
    global config_params_server
    use_gcs_config_server = os.getenv('USE_GCS_CONFIG_SERVER')

    if use_gcs_config_server and use_gcs_config_server  == 'True':
        project_id = os.getenv('PROJECT_ID')
        if project_id:
            gcs_bucket_name = f'gcs_config_bucket_{project_id}'
            gcs_file_name = 'config_params.json'
            config_params_server = config_server.GcsConfigServer(gcs_bucket_name, gcs_file_name)

    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080
    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host='127.0.0.1', port=PORT, debug=True)


if __name__ == '__main__':
    main()
