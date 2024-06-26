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

variable "project_id" {
  type        = string
  description = "The project ID."
}

variable "topic" {
  type        = string
  description = "The Cloud PubSub topic."
}

# For Pubsub push subscription, see https://cloud.google.com/pubsub/docs/push.
variable "push_subscription" {
    type = object({
        name    = string
        push_endpoint = string
    })
    description = "The Pubsub push subscripton name and endpoint."
}

variable "cloud_run_invoker_service_account_email" {
  type        = string
  description = "Service account used by Pubsub Push subscriptions to invoke Cloud Run service."
}