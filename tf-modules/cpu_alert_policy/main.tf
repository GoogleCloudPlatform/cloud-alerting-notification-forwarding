# Copyright 2021 Google LLC
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

# TF module that creates a sample cpu alert policy.

# Create a Pubsub channel.
module "pubsub_channel" {
  source                  = "../../tf-modules/pubsub_channel"

  topic                   = var.topic
  project_id              = var.project_id
  cloud_run_invoker_service_account_email = var.cloud_run_invoker_service_account_email

  push_subscription = var.push_subscription
}

# Create a sample alert policy with the Cloud Pubsub notification channel.
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy
resource "google_monitoring_alert_policy" "alert_policy" {
  display_name = "Sample Alert Policy: ${var.topic}"
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
  user_labels = {
    severity = "p1"
  }
  notification_channels =[module.pubsub_channel.notif_channel]
}