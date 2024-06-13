# Copyright 2021 Google LLC.
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
  cpu_pubsub_topic = "tf-topic-cpu"
  disk_pubsub_topic = "tf-topic-disk"
}

provider "google" {
  project = var.project_id
  version = "~> 3.65"  
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

# Setup a CPU usage alerting policy using a Pubsub channel.
module "cpu_alert_policy" {
  source                  = "../../tf-modules/cpu_alert_policy"

  topic                   = local.cpu_pubsub_topic
  project_id              = "${var.project_id}"
  cloud_run_invoker_service_account_email = "${module.pubsub_service.cloud_run_invoker_service_account_email}"

  push_subscription = {
      name              = "alert-push-subscription-cpu"
      push_endpoint     = "${module.cloud_run.url}/${local.cpu_pubsub_topic}"
  }  
}

# Setup a disk usage alerting policy using a Pubsub channel.
module "disk_alert_policy" {
  source                  = "../../tf-modules/disk_alert_policy"

  topic                   = local.disk_pubsub_topic
  project_id              = "${var.project_id}"
  cloud_run_invoker_service_account_email = "${module.pubsub_service.cloud_run_invoker_service_account_email}"

  push_subscription = {
      name              = "alert-push-subscription-disk"
      push_endpoint     = "${module.cloud_run.url}/${local.disk_pubsub_topic}"
  }  
}