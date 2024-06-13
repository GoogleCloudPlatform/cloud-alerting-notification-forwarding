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

# The code in this module is based on
# https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/run/pubsub/main.py.
# See https://cloud.google.com/run/docs/tutorials/pubsub for the accompanying
# Cloud Run/PubSub solutions guide.

"""Runs Cloud Alerting Notification Integration app with Flask."""
# Imports the Cloud Logging client library
import google.cloud.logging

# Instantiates a client
client = google.cloud.logging.Client()

# Retrieves a Cloud Logging handler based on the environment
# you're running in and integrates the handler with the
# Python logging module. By default this captures all logs
# at INFO level and higher
# See https://cloud.google.com/logging/docs/reference/libraries#write_standard_logs
client.setup_logging()

import logging
import json
import sys
import os

from flask import Flask, request

from httplib2 import Http

from utilities import config_server, pubsub, service_handler


# The keys of the config_map corresponds to the local pubsub topic
# variables in main.tf.
config_map = {
    'tf-topic-cpu': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': 'https://chat.googleapis.com/v1/spaces/AAAAjOjX3I0/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=e9mcRhsfwYw51zvyTJ5ckw7YVC8ViR8bl7dtP8UrJGY%3D',
    },
    'tf-topic-disk': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': 'https://chat.googleapis.com/v1/spaces/AAAA9xJV6L8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=cgLW9UExTH8kipz2cBOaj51LOa4d2OJmdsXJkX8-Fas%3D',
    },
}
# By default, we use the in-memory config server created in the above code.
# If the env. variable 'CONFIG_SERVER_TYPE' is set to 'gcs', we will use
# a GCS config server. The GCS bucket name is gcs_config_bucket_{PROJECT_ID} and the
# config file/object name is gcs_config_file.json.
# If you want to use the GCS config file, don't forget to manually create the GCS
# bucket and upload the config file to the bucket before running the deployment
# script.
config_params_server = config_server.InMemoryConfigServer(config_map)
config_server_type = os.getenv('CONFIG_SERVER_TYPE')
logging.info(f'The config server type : {config_server_type}')
if config_server_type and config_server_type == 'gcs':
  project_id = os.getenv('PROJECT_ID')
  if project_id:
    gcs_bucket_name = f'gcs_config_bucket_{project_id}'
    gcs_file_name = 'config_params.json'
    config_params_server = config_server.GcsConfigServer(
        gcs_bucket_name, gcs_file_name
    )
    logging.info(
        'The GCS bucket config server is used :'
        f' {gcs_bucket_name}/{gcs_file_name}'
    )
  else:
    logging.info(
        'The in-memory config server is used even it is configured:'
        f' project_id={project_id}'
    )

gchat_handler = service_handler.GchatHandler()
service_names_to_handlers = {
    'google_chat': gchat_handler,
}

app = Flask(__name__)


# Note: we need to return 200 status code to ack the PubSub message, even the notification delivery
# is failed with non-retriable errors. For retriable errors, we can return non-(100, 20x) error codes
# to request Pubsub to resend the message.
# See https://cloud.google.com/pubsub/docs/push#receiving_messages for more details.
# The returned response string is in the formate of "{status_code}:{message}", where the status_code
# is the real status code returned by the integration service and the message is a detailed response
# messsage string.
@app.route('/<config_id>', methods=['POST'])
def handle_pubsub_message(config_id):
  try:
    config_param = config_params_server.GetConfig(config_id)
  except BaseException as e:
    err_msg = 'Failed to get config parameters for {}: {}'.format(config_id, e)
    logging.error(err_msg)
    return (f'500: {err_msg}', 200)
  if 'service_name' not in config_param:
    err_msg = '"service_name" not found in the config parameters: {}'.format(
        config_id
    )
    logging.error(err_msg)
    return (f'500: {err_msg}', 200)
  if config_param['service_name'] not in service_names_to_handlers:
    err_msg = 'No handler found for the service {}'.format(
        config_param['service_name']
    )
    logging.error(err_msg)
    return (f'500: {err_msg}', 200)

  handler = service_names_to_handlers[config_param['service_name']]

  # Parse the Pub/Sub raw message to get the notification
  pubsub_received_message = request.get_json()
  try:
    notification = pubsub.ExtractNotificationFromPubSubMsg(
        pubsub_received_message
    )
    response, status_code = handler.SendNotification(config_param, notification)
    logging.info(
        f'Notification was sent with the status code = {status_code}:'
        f' {response}'
    )
    return (f'{status_code}: {response}', 200)
  except pubsub.DataParseError as e:
    logging.error(f'Pubsub message parse error: {e}')
    return (f'400: {e}', 200)
  except BaseException as e:
    logging.error(f'Unexpected error when processing Pubsub message: {e}')
    return (f'400: {e}', 200)


def main():
  PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080
  # This is used when running locally. Gunicorn is used to run the
  # application on Cloud Run. See entrypoint in Dockerfile.
  app.run(host='127.0.0.1', port=PORT, debug=True)


if __name__ == '__main__':
  main()
