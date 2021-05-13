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
  pubsub_topic = "tf-topic-wdzc"
}
provider "google" {
  project = var.project
}
module "pubsub" {
  source  = "../../modules/pubsub"
  
  topic              = local.pubsub_topic
  project            = "${var.project}"

  push_subscription = {
      name              = "alert-push-subscription-wdzc"
      push_endpoint     = "${module.cloud_run_with_pubsub.url}/${local.pubsub_topic}"
  }
}

module "cloud_run_with_pubsub" {
  source  = "../../modules/cloud_run_with_pubsub"
  project = "${var.project}"
  
  pubsub_service_account_email = "${module.pubsub.pubsub_service_account_email}"
}

module "pubsub_channels_and_policies" {
  source                  = "../../modules/pubsub_channels_and_policies"
  topic                   = module.pubsub.topic
  project_id              = "${var.project}"
}