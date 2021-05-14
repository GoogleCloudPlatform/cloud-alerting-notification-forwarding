# Copyright 2020 Google LLC
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

# Grant Google Monitoring Service Account the Pubsub publish role. This is needed to publish notification in the 
# given Cloud PubSub channel.
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/pubsub_topic_iam#google_pubsub_topic_iam_binding

# To get the project number.
data "google_project" "project" {
    project_id = var.project_id
}

# Creates a PubSub topic for the PubSub channel.
resource "google_pubsub_topic" "tf" {
  name       = var.topic
  project    = var.project_id
}

resource "google_pubsub_subscription" "push" {
  name = var.push_subscription.name
  topic = google_pubsub_topic.tf.name
  
  push_config {
    push_endpoint = var.push_subscription.push_endpoint
    oidc_token {
      service_account_email = var.pubsub_service_account_email
    }
  }
}

# To enable the Cloud PubSub channel as a publisher.
resource "google_pubsub_topic_iam_binding" "binding" {
  project = var.project_id
  topic = var.topic
  role = "roles/pubsub.publisher"  
  members = [
      "serviceAccount:service-${data.google_project.project.number}@gcp-sa-monitoring-notification.iam.gserviceaccount.com"
  ]
  depends_on = [google_monitoring_notification_channel.pubsub]
}

# Create Cloud Pubsub notification channels.
# See https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_notification_channel
resource "google_monitoring_notification_channel" "pubsub" {
  display_name = "Cloud Pubsub Notification Channel for ${var.topic}"
  type         = "pubsub"
  labels = {
    topic = google_pubsub_topic.tf.id
  }
}