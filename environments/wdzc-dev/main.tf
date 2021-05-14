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


locals {
  cpu_pubsub_topic = "tf-topic-wdzc-cpu"
  disk_pubsub_topic = "tf-topic-wdzc-disk"
}

provider "google" {
  project = var.project
  version = "~> 3.65"  
}

# Setup all pubsub related services and service accounts.
module "pubsub_service" {
  source  = "../../modules/pubsub_service"

  project            = "${var.project}"
}

# Setup the Cloud Run service.
module "cloud_run" {
  source  = "../../modules/cloud_run"

  project = "${var.project}"
  pubsub_service_account_email = "${module.pubsub_service.pubsub_service_account_email}"
}

# Setup a CPU usage alerting policy and its gchat notifcation channel.
module "cpu_alert_policy" {
  source                  = "../../modules/cpu_alert_policy"

  topic                   = local.cpu_pubsub_topic
  project_id              = "${var.project}"
  pubsub_service_account_email = "${module.pubsub_service.pubsub_service_account_email}"

  push_subscription = {
      name              = "alert-push-subscription-wdzc-cpu"
      push_endpoint     = "${module.cloud_run.url}/${local.cpu_pubsub_topic}"
  }  
}
