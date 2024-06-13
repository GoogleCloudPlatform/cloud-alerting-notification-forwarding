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

# TF module that sets up Cloud PubSub related resources and service accounts.

# Enable the Cloud PubSub service.
resource "google_project_service" "pubsub" {
  service  = "pubsub.googleapis.com"
  project  = var.project_id
}

# Enable the Cloud IAM service.
resource "google_project_service" "iam" {
  service  = "iam.googleapis.com"
  project  = var.project_id
}

data "google_project" "project" {}

# Grant permission to the Pub/Sub default service account to create authentication tokens for the
# service account generated below to invoke Cloud Run service.
resource "google_project_iam_binding" "project" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"

  # Default Pubsub service account, see 
  # https://cloud.google.com/pubsub/docs/push#setting_up_for_push_authentication.
  members = [
    "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  ]
}

# Create a service account used to invoke the Cloud Run server.
resource "google_service_account" "service_account" {
  account_id   = "cloud-run-pubsub-invoker-sa"
  display_name = "Service account used by Pubsub "
  project      = var.project_id
  depends_on = [google_project_service.iam]
}