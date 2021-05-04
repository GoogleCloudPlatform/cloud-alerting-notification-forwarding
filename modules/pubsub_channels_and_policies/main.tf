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
  display_name = "Cloud Pubsub Notification Channel for wdzc"
  type         = "pubsub"
  labels = {
    topic = var.topic
  }
  depends_on = [var.pubsub_topic_depends_on]
}

# Create an alert policy with a Cloud Pubsub notification channel
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy
resource "google_monitoring_alert_policy" "alert_policy" {
  display_name = "wdzc Alert Policy"
  combiner     = "OR"
  conditions {
    display_name = "test condition"
    condition_threshold {
      filter     = "metric.type=\"compute.googleapis.com/instance/cpu/usage_time\" AND resource.type=\"gce_instance\""
      duration   = "60s"
      comparison = "COMPARISON_GT"
      threshold_value = 0
      trigger {
        count = 1
      }
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"       
      }
    }
  }
  notification_channels =[google_monitoring_notification_channel.pubsub.name]
}