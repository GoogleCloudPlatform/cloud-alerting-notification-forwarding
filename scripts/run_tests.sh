#!/bin/bash

export FLASK_APP_ENV=test
pytest philips_hue_integration_example
pytest jira_integration_example/tests/jira_notification_handler_test.py
pytest jira_integration_example/tests/main_test.py
