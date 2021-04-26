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

# Note: Multiple copies of this test cannot be executed in parallel, since they allocate
# resources using constants and would interfere with each other.

# TODO(https://github.com/googleinterns/cloud-monitoring-notification-delivery-integration-sample-code/issues/83): Refactor scripts/incident_script.py to also use these constants.

from google.protobuf.duration_pb2 import Duration

# caller is required to fill in the metric name
METRIC_PATH = 'custom.googleapis.com/{METRIC_NAME}'
RESOURCE_TYPE = 'gce_instance'
INSTANCE_ID = '1234567890123456789'
ZONE = 'us-central1-f'
TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE = 3.0


TEST_METRIC_DESCRIPTOR_TEMPLATE = {
    'type': METRIC_PATH,
    'metric_kind': 'GAUGE',
    'value_type': 'DOUBLE',
    'description': 'A custom metric meant for testing purposes'
}

TEST_NOTIFICATION_CHANNEL_TEMPLATE = {
    'type': 'pubsub',
    'display_name': 'test channel',
    'description': 'A Pub/Sub channel meant for testing purposes',
    'labels': {
        # caller is required to fill in the project_id
        'topic': 'projects/{PROJECT_ID}/topics/tf-topic'
    }
}

TEST_ALERT_POLICY_TEMPLATE = {
    # caller is required to fill in the alert policy name
    'display_name': '{ALERT_POLICY_NAME}',
    'user_labels': {'type': 'test_policy', 'metric': '{METRIC_NAME}'},
    'combiner': 'AND',
    'conditions': [{
        'display_name': 'test condition',
        'condition_threshold': {
            # caller is required to fill in the metric path
            'filter': 'metric.type = "{METRIC_PATH}" AND ' + f'resource.type = "{RESOURCE_TYPE}"',
            'comparison': 'COMPARISON_GT',
            'threshold_value': TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE,
            'duration': Duration(seconds=0),
        }
    }],
    'notification_channels': []
}
