#!/bin/bash
cd notification_integration
python3 -m unittest utilities.service_handler_test
python3 -m unittest utilities.config_server_test