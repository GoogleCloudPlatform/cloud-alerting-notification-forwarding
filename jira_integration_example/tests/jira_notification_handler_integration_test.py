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

import time
import functools
from copy import deepcopy

import pytest

from google.cloud import monitoring_v3
from google.api_core import exceptions
from google.api_core import retry
from jira import JIRA

import main
from tests import constants


@retry.Retry(predicate=retry.if_exception_type(exceptions.GoogleAPICallError), deadline=10)
def short_retry(callable_function, *args):
    return callable_function(*args)


@retry.Retry(predicate=retry.if_exception_type(AssertionError), deadline=180)
def long_retry(callable_function, *args):
    return callable_function(*args)


@pytest.fixture
def config():
    return main.app.config


@pytest.fixture
def jira_client(config):
    # setup
    oauth_dict = {'access_token': config['JIRA_ACCESS_TOKEN'],
                  'access_token_secret': config['JIRA_ACCESS_TOKEN_SECRET'],
                  'consumer_key': config['JIRA_CONSUMER_KEY'],
                  'key_cert': config['JIRA_KEY_CERT']}
    jira_client = JIRA(config['JIRA_URL'], oauth=oauth_dict)

    yield jira_client

    # tear down
    test_issues = jira_client.search_issues('summary~"test condition"')
    for issue in test_issues:
        issue.delete()


@pytest.fixture
def metric_descriptor(config, request):
    def create_metric_descriptor(metric_name):
        # setup
        metric_client = monitoring_v3.MetricServiceClient()
        gcp_project_path = metric_client.project_path(config['PROJECT_ID'])

        test_metric_descriptor = deepcopy(constants.TEST_METRIC_DESCRIPTOR_TEMPLATE)
        test_metric_descriptor['type'] = test_metric_descriptor['type'].format(METRIC_NAME=metric_name)

        metric_descriptor = metric_client.create_metric_descriptor(
            gcp_project_path,
            test_metric_descriptor)
        metric_descriptor = short_retry(metric_client.get_metric_descriptor, metric_descriptor.name)

        # tear down (addfinalizer is called after the test finishes execution)
        request.addfinalizer(functools.partial(metric_client.delete_metric_descriptor, metric_descriptor.name))

        return metric_descriptor

    return create_metric_descriptor


@pytest.fixture
def notification_channel(config):
    # setup
    notification_channel_client = monitoring_v3.NotificationChannelServiceClient()
    gcp_project_path = notification_channel_client.project_path(config['PROJECT_ID'])
    test_notification_channel = constants.TEST_NOTIFICATION_CHANNEL_TEMPLATE
    test_notification_channel['labels']['topic'] = constants.TEST_NOTIFICATION_CHANNEL_TEMPLATE['labels']['topic'].format(PROJECT_ID=config['PROJECT_ID'])

    notification_channel = notification_channel_client.create_notification_channel(
        gcp_project_path,
        test_notification_channel)
    notification_channel = short_retry(notification_channel_client.get_notification_channel,
                                       notification_channel.name)

    yield notification_channel

    # tear down
    notification_channel_client.delete_notification_channel(notification_channel.name)


@pytest.fixture
def alert_policy(config, notification_channel, request):
    def create_alert_policy(alert_policy_name, metric_name):
        # setup
        policy_client = monitoring_v3.AlertPolicyServiceClient()
        gcp_project_path = policy_client.project_path(config['PROJECT_ID'])

        test_alert_policy = deepcopy(constants.TEST_ALERT_POLICY_TEMPLATE)
        test_alert_policy['notification_channels'].append(notification_channel.name)
        test_alert_policy['display_name'] = alert_policy_name
        test_alert_policy['user_labels']['metric'] = metric_name
        metric_path = constants.METRIC_PATH.format(METRIC_NAME=metric_name)
        test_alert_policy['conditions'][0]['condition_threshold']['filter'] = test_alert_policy['conditions'][0]['condition_threshold']['filter'].format(METRIC_PATH=metric_path)

        alert_policy = policy_client.create_alert_policy(
            gcp_project_path,
            test_alert_policy)
        alert_policy = short_retry(policy_client.get_alert_policy, alert_policy.name)

        # tear down (addfinalizer is called after the test finishes execution)
        request.addfinalizer(functools.partial(policy_client.delete_alert_policy, alert_policy.name))

        return alert_policy

    return create_alert_policy


def append_to_time_series(config, metric_name, point_value):
    client = monitoring_v3.MetricServiceClient()
    gcp_project_path = client.project_path(config['PROJECT_ID'])

    series = monitoring_v3.types.TimeSeries()
    series.metric.type = constants.METRIC_PATH.format(METRIC_NAME=metric_name)
    series.resource.type = constants.RESOURCE_TYPE
    series.resource.labels['instance_id'] = constants.INSTANCE_ID
    series.resource.labels['zone'] = constants.ZONE
    point = series.points.add()
    point.value.double_value = point_value
    now = time.time()
    point.interval.end_time.seconds = int(now)
    point.interval.end_time.nanos = int(
        (now - point.interval.end_time.seconds) * 10**9)

    client.create_time_series(gcp_project_path, [series])


def test_open_close_ticket(config, metric_descriptor, notification_channel, alert_policy, jira_client):
    # Sanity check that the test fixtures were initialized with values that the rest of the test expects
    metric_descriptor = metric_descriptor('integ-test-metric')
    alert_policy = alert_policy('integ-test-policy', 'integ-test-metric')

    assert metric_descriptor.type == constants.TEST_METRIC_DESCRIPTOR_TEMPLATE['type'].format(METRIC_NAME='integ-test-metric')
    assert notification_channel.display_name == constants.TEST_NOTIFICATION_CHANNEL_TEMPLATE['display_name']
    assert alert_policy.display_name == 'integ-test-policy'
    assert alert_policy.notification_channels[0] == notification_channel.name

    def assert_jira_issue_is_created():
        # Search for all issues where the status is 'unresolved' and
        # the integ-test-metric custom field is set to this the Cloud Monitoring project ID
        project_id = config['PROJECT_ID']
        query_string = f'description~"custom/integ-test-metric for {project_id}" and status=10000'
        created_monitoring_issues = jira_client.search_issues(query_string)
        assert len(created_monitoring_issues) == 1

    def assert_jira_issue_is_resolved():
        # Search for all issues where the status is 'resolved' and
        # the integ-test-metric custom field is set to this the Cloud Monitoring project ID
        project_id = config['PROJECT_ID']
        query_string = f'description~"custom/integ-test-metric for {project_id}" and status={config["CLOSED_JIRA_ISSUE_STATUS"]}'
        resolved_monitoring_issues = jira_client.search_issues(query_string)
        assert len(resolved_monitoring_issues) == 1

    # trigger incident and check jira issue created
    append_to_time_series(config, 'integ-test-metric', constants.TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE + 1)
    long_retry(assert_jira_issue_is_created) # issue status id for "To Do"

    # resolve incident and check jira issue resolved
    append_to_time_series(config, 'integ-test-metric', constants.TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE)
    long_retry(assert_jira_issue_is_resolved)


def test_open_resolve_multiple_tickets(config, metric_descriptor, notification_channel, alert_policy, jira_client):
    # Sanity check that the test fixtures were initialized with values that the rest of the test expects
    metric_descriptor_1 = metric_descriptor('integ-test-metric-1')
    alert_policy_1 = alert_policy('integ-test-policy-1', 'integ-test-metric-1')
    metric_descriptor_2 = metric_descriptor('integ-test-metric-2')
    alert_policy_2 = alert_policy('integ-test-policy-2', 'integ-test-metric-2')

    assert notification_channel.display_name == constants.TEST_NOTIFICATION_CHANNEL_TEMPLATE['display_name']
    assert metric_descriptor_1.type == constants.TEST_METRIC_DESCRIPTOR_TEMPLATE['type'].format(METRIC_NAME='integ-test-metric-1')
    assert alert_policy_1.display_name == 'integ-test-policy-1'
    assert alert_policy_1.notification_channels[0] == notification_channel.name
    assert metric_descriptor_2.type == constants.TEST_METRIC_DESCRIPTOR_TEMPLATE['type'].format(METRIC_NAME='integ-test-metric-2')
    assert alert_policy_2.display_name == 'integ-test-policy-2'
    assert alert_policy_2.notification_channels[0] == notification_channel.name

    def assert_jira_issues_are_created(metric_names):
        # Search for all issues where the status is 'unresolved' and
        # the integ-test-metric custom field is set to this the Cloud Monitoring project ID
        project_id = config['PROJECT_ID']
        for metric_name in metric_names:
            query_string = f'description~"custom/{metric_name} for {project_id}" and status=10000' # issue status for To Do
            created_monitoring_issues = jira_client.search_issues(query_string)
            assert len(created_monitoring_issues) == 1

    def assert_jira_issues_are_resolved(metric_names):
        # Search for all issues where the status is 'resolved' and
        # the integ-test-metric custom field is set to this the Cloud Monitoring project ID
        project_id = config['PROJECT_ID']
        for metric_name in metric_names:
            query_string = f'description~"custom/{metric_name} for {project_id}" and status={config["CLOSED_JIRA_ISSUE_STATUS"]}'
            resolved_monitoring_issues = jira_client.search_issues(query_string)
            assert len(resolved_monitoring_issues) == 1

    # trigger incident for integ-test-policy-1 and check jira issue created
    append_to_time_series(config, 'integ-test-metric-1', constants.TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE + 1)
    long_retry(assert_jira_issues_are_created, ['integ-test-metric-1'])

    # trigger incident for integ-test-policy-2 and check issues for policy 1 and 2 exist
    append_to_time_series(config, 'integ-test-metric-2', constants.TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE + 1)
    long_retry(assert_jira_issues_are_created, ['integ-test-metric-1', 'integ-test-metric-2'])

    # resolve incident for integ-test-policy-1 and check jira issue resolved for policy 1, unresolved for 2
    append_to_time_series(config, 'integ-test-metric-1', constants.TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE)
    long_retry(assert_jira_issues_are_resolved, ['integ-test-metric-1'])
    long_retry(assert_jira_issues_are_created, ['integ-test-metric-2'])

    # resolve incident for integ-test-policy-2 and check both jira issues are resolved
    append_to_time_series(config, 'integ-test-metric-2', constants.TRIGGER_NOTIFICATION_THRESHOLD_DOUBLE)
    long_retry(assert_jira_issues_are_resolved, ['integ-test-metric-1', 'integ-test-metric-2'])
