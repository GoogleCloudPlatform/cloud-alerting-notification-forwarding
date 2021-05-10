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


output "topic" {
  value       = "${google_pubsub_topic.tf.id}"
  description = "The generated PubSub topic in the format 'projects/xxx/topics/yyy'"
}

output "pubsub_service_account_email" {
  value       = "${google_service_account.service_account.email}"
  description = "The service account used to authenticate the Https requests sent to the Cloud Run service"
}