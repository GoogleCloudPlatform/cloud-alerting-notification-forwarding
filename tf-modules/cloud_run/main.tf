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

# TF module that sets up a Cloud Run service that integrates Google Cloud
# Alerting PubSub notification channels with 3rd-party services, e.g.
# Google Chat. It also grants the invoker role to the service account
# used by the push subscriptions of the PubSub notification channels that
# automatically forward the PubSub messages to the Cloud Run server.

# Enables the Cloud Run service.
# Note: The Service Usage API must be enabled to use this resource.
resource "google_project_service" "run" {
  service  = "run.googleapis.com"
  project  = var.project_id
}

# Creates a Cloud Run service using a docker image saved in Container Registry.
resource "google_cloud_run_service" "cloud_run_pubsub_service" {
  name     = "cloud-run-pubsub-service"
  location = "us-east1"
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/cloud-run-pubsub-service:latest"
      }
    }
    metadata {
      # Use uuid() to generate a unique name.
      name = "cloud-run-pubsub-service-${uuid()}"
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
  # Wait for the Cloud Run service to be enabled first.
  depends_on = [google_project_service.run]
}

# Grant the service account that represents the push subscriptions of the
# Cloud Alerting PubSub notifications channels (i.e. topics) the invoke
# role of the Cloud Run service.
# More details can be found at
# https://cloud.google.com/run/docs/tutorials/pubsub#integrating-pubsub
resource "google_cloud_run_service_iam_binding" "binding" {
  location  = google_cloud_run_service.cloud_run_pubsub_service.location
  project   = google_cloud_run_service.cloud_run_pubsub_service.project
  service   = google_cloud_run_service.cloud_run_pubsub_service.name
  role      = "roles/run.invoker"
  members   = [
    "serviceAccount:${var.cloud_run_invoker_service_account_email}"
  ]
}