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

# Enable the Cloud PubSub service.
resource "google_project_service" "pubsub" {
  service  = "pubsub.googleapis.com"
  project  = var.project
  disable_dependent_services=true   
}

# Enable the Cloud IAM service.
resource "google_project_service" "iam" {
  service  = "iam.googleapis.com"
  project  = var.project
}

# Creates a PubSub topic for the PubSub channel.
resource "google_pubsub_topic" "tf" {
  name       = var.topic
  project    = var.project
  depends_on = [google_project_service.pubsub]
}

# Service account used to generate the auth. tokens attached to the Https requests sent to the Cloud Run server.
resource "google_service_account" "service_account" {
  account_id   = "cloud-run-pubsub-invoker-wdzc"
  display_name = "Cloud Run Pubsub Invoker created by wdzc"
  project      = var.project
  depends_on = [google_project_service.iam]
}

resource "google_pubsub_subscription" "push" {
  name = var.push_subscription.name
  topic = google_pubsub_topic.tf.name
  
  
  push_config {
    push_endpoint = var.push_subscription.push_endpoint
    oidc_token {
      service_account_email = google_service_account.service_account.email
    }
  }
}

data "google_project" "project" {}

# enable Pub/Sub to create authentication tokens in the project
resource "google_project_iam_binding" "project" {
  project = var.project
  role    = "roles/iam.serviceAccountTokenCreator"

  # Service account created by default.
  members = [
    "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  ]
}
