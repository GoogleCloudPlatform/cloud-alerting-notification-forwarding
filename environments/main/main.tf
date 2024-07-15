# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Main TF module.

locals {
  cpu_pubsub_topic_teams = "tf-topic-cpu-teams"
  cpu_pubsub_topic_gchat = "tf-topic-cpu-gchat"
  disk_pubsub_topic_teams = "tf-topic-disk-teams"
  disk_pubsub_topic_gchat = "tf-topic-disk-gchat"
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 3.65"
    }
  }
}

# Setup all pubsub related services and service accounts.
module "pubsub_service" {
  source  = "../../tf-modules/pubsub_service"

  project_id            = "${var.project_id}"
}

# Setup the Cloud Run service.
module "cloud_run" {
  source  = "../../tf-modules/cloud_run"

  project_id = "${var.project_id}"
  cloud_run_invoker_service_account_email = "${module.pubsub_service.cloud_run_invoker_service_account_email}"
}

# Setup a CPU usage alerting policy using a Pubsub channel for gchat.
module "cpu_alert_policy_gchat" {
  source                  = "../../tf-modules/cpu_alert_policy_gchat"

  topic                   = local.cpu_pubsub_topic_gchat
  project_id              = "${var.project_id}"
  cloud_run_invoker_service_account_email = "${module.pubsub_service.cloud_run_invoker_service_account_email}"

  push_subscription = {
      name              = "alert-push-subscription-cpu_gchat"
      push_endpoint     = "${module.cloud_run.url}/${local.cpu_pubsub_topic_gchat}"
  }
}

# Setup a CPU usage alerting policy using a Pubsub channel for teams.
module "cpu_alert_policy_teams" {
  source = "../../tf-modules/cpu_alert_policy_teams"

  topic = local.cpu_pubsub_topic_teams
  project_id = var.project_id
  cloud_run_invoker_service_account_email = module.pubsub_service.cloud_run_invoker_service_account_email

  push_subscription = {
    name          = "alert-push-subscription-cpu_teams"
    push_endpoint = "${module.cloud_run.url}/${local.cpu_pubsub_topic_teams}"
  }

  link_display_name = var.link_display_name
  link_url          = var.link_url
}

# Setup a disk usage alerting policy using a Pubsub channel for gchat.
module "disk_alert_policy_gchat" {
  source                  = "../../tf-modules/disk_alert_policy_gchat"

  topic                   = local.disk_pubsub_topic_gchat
  project_id              = "${var.project_id}"
  cloud_run_invoker_service_account_email = "${module.pubsub_service.cloud_run_invoker_service_account_email}"

  push_subscription = {
      name              = "alert-push-subscription-disk_gchat"
      push_endpoint     = "${module.cloud_run.url}/${local.disk_pubsub_topic_gchat}"
  }
}

# Setup a disk usage alerting policy using a Pubsub channel for teams.
module "disk_alert_policy_teams" {
  source                  = "../../tf-modules/disk_alert_policy_teams"

  topic                   = local.disk_pubsub_topic_teams
  project_id              = "${var.project_id}"
  cloud_run_invoker_service_account_email = "${module.pubsub_service.cloud_run_invoker_service_account_email}"

  push_subscription = {
      name              = "alert-push-subscription-disk_teams"
      push_endpoint     = "${module.cloud_run.url}/${local.disk_pubsub_topic_teams}"
  }
  link_display_name = var.link_display_name
  link_url          = var.link_url
}