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
resource "google_pubsub_topic_iam_binding" "binding" {
  project = google_pubsub_topic.tf.project
  topic = google_pubsub_topic.tf.name
  role = "roles/pubsub.publisher"
  member = "serviceAccount:service-663007850766@gcp-sa-monitoring-notification.iam.gserviceaccount.com"
}

# Create Cloud Pubsub notification channels.
# See https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_notification_channel
resource "google_monitoring_notification_channel" "basic" {
  display_name = "Test Notification Channel"
  type         = "pubsub"
  labels = {
    topic = var.topic
  }
}

data "google_monitoring_notification_channel" "basic" {
  display_name = "Test Notification Channel"
}

# Create an alert policy with a Cloud Pubsub notification channel
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy
resource "google_monitoring_alert_policy" "alert_policy" {
  display_name = "wdzc Alert Policy"
  combiner     = "OR"
  conditions {
    display_name = "test condition"
    condition_threshold {
      filter     = "metric.type=\"compute.googleapis.com/instance/disk/write_bytes_count\" AND resource.type=\"gce_instance\""
      duration   = "60s"
      comparison = "COMPARISON_GT"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  notification_channels =[data.google_monitoring_notification_channel.basic.name]
  user_labels = {
    foo = "bar"
  }
}
