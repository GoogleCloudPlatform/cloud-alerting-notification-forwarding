# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TF module that creates a Google Alerting Pubsub notification channel,
# including the Pubsub topic and push subscription.

# To get the project number
data "google_project" "project" {
    project_id = var.project_id
}

# Create a PubSub topic for the PubSub channel.
resource "google_pubsub_topic" "tf" {
  name       = var.topic
  project    = var.project_id
}

# Create a Pubsub push subscription that uses the given service
# account to invoke the Cloud Run service.
resource "google_pubsub_subscription" "push" {
  name  = var.push_subscription.name
  project = var.project_id
  topic = google_pubsub_topic.tf.name

  push_config {
    push_endpoint = var.push_subscription.push_endpoint
    # Use the tokens of the given service account to authenticate/authorize
    # with the Cloud Run service as invoker.
    oidc_token {
      service_account_email = var.cloud_run_invoker_service_account_email
    }
  }
}

# Grant the monitoring default service account the publisher role of the
# created cloud PubSub channel.
# Note: The monitoring default service account will be automatically created
# when the first Pubsub notification channel is created. So wait for the pubsub
# channel to be ready first.
# The service account is service-xxx@gcp-sa-monitoring-notification.iam.gserviceaccount.com
# where "xxx" is the project number.
# See https://cloud.google.com/monitoring/support/notification-options#pubsub
resource "google_pubsub_topic_iam_binding" "binding" {
  project = var.project_id
  topic = google_pubsub_topic.tf.name # Topic name should be extracted from google_pubsub_topic
  role    = "roles/pubsub.publisher"
  members = [
      "serviceAccount:service-${data.google_project.project.number}@gcp-sa-monitoring-notification.iam.gserviceaccount.com"
  ]
  depends_on = [google_monitoring_notification_channel.pubsub]
}

# Creates Cloud Pubsub notification channels.
# See https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_notification_channel
resource "google_monitoring_notification_channel" "pubsub" {
  display_name = "Cloud Pubsub Notification Channel for ${var.topic}"
  type         = "pubsub"
  project = var.project_id
  labels = {
    topic = google_pubsub_topic.tf.id
  }
}