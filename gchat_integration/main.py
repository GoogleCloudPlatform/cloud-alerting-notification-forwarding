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
config_server = config_server.HardCodedConfigServer()
gchat_handler = service_handler.GchatHandler()
service_names_to_handlers = {
    'google_chat': gchat_handler,
}

app = Flask(__name__)

# [START run_pubsub_handler]
@app.route('/<config_id>', methods=['POST'])
def handle_pubsub_message(config_id):
    try:
        config_param = config_server.GetConfigParam(config_id)
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
    except pubsub.DataParseError as e:
        logger.error(e)
        return (str(e), 400)

    try:
        handler.SendNotification(config_param, notification)
    except BaseException as e:
        logger.error(e)
        return (str(e), 400)
    return (str(notification) ,200)    
# [END run_pubsub_handler]

  
if __name__ == '__main__':
    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080
    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host='127.0.0.1', port=PORT, debug=True)