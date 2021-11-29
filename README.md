# Sample Code for the Cloud Monitoring Alerting Notification Delivery Integration Guide

**This is not an officially supported Google product.**

This repository provides examples of how a Google Cloud user can forward **[alerting notifications](https://cloud.google.com/monitoring/alerts#how_does_alerting_work)** to third-party integrations not officially supported as **[notification channels](https://cloud.google.com/monitoring/support/notification-options)**. The provided example forwards alerting notifications to  Google chat rooms via Cloud Pus/Sub notification channels. The example accomplishes this through the use of a Flask server running on Cloud Run which receives alerting notifications from Cloud Pub/Sub notification channels, parses them into Google chat messages, and then delivers the messages to Google chat rooms via HTTP requests.

The sample code in this repository is referenced in this **[Cloud Community tutorial](To Be Updated)**. 

## Folder Structure

    .
    ├── .github/workflows
    ├── environments                      # Terraform configurations for each environment
    │   ├── main                          #   GitHub main branch
    ├── tf-modules                        # Terraform modules
    │   ├── cloud_run                     #   Cloud run module    
    │   ├── cpu_alert_policy              #   Sample CPU alert policy module
    │   ├── disk_alert_policy             #   Sample disk alert policy module
    │   ├── pubsub_channel                #   Cloud Pub/Sub notification channel module
    │   ├── pubsub_service                #   Cloud Pub/Sub service (e.g. topics, subscriptions) module
    ├── notification_integration          # Alerting notification integration
    │   ├── utilities                     #   Notification integration sub-modules and their unit tests
    ├── scripts                           # Scripts for testing
    .
    .
    .
    ├── deploy.py                         # Deployment script.
    └── cloudbuild.yaml                   # Cloud build configuration file

## Setup

1. Create a [new Google Cloud Platform project from the Cloud
   Console](https://console.cloud.google.com/project) or use an existing empty project.

2. Be sure to [enable billing](https://cloud.google.com/billing/docs/how-to/modify-project) in your new GCP project.

3. Click the "Open in Cloud Shell" button below to clone and open this repository on Cloud Shell.

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgooglecloudplatform%2Fcloud-alerting-notification-channel-integration-operations)

## One Button / Automatic deployment

To deploy the notification channel integration sample for the first time automatically, we've provided a script `deploy.py` that will handle a majority of the required actions for deployment. Complete the following steps before running the script.

1. Ensure Python 3.5 or higher is installed in Cloud Shell. Run the following command to check. More information about how to set up a Python development environment can be found at [here](https://cloud.google.com/python/docs/setup).
  ```
  python3 --version
  ```

2. In `~/notification_integration/main.py` edit the `config_map` dictionary replacing the webhook_url with your own Google Chat webhook url. 
```
config_map = {
    'tf-topic-cpu': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': '<YOUR_GOOGLE_CHAT_ROOM_WEBHOOK_URL>'},
    'tf-topic-disk': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': '<YOUR_GOOGLE_CHAT_ROOM_WEBHOOK_URL>'}
}
```

3. Run the script with the following command:
  ```
  python3 deploy.py -p <PROJECT_ID>
  ```

## Manual Deployment

To deploy the notification channel integration sample manually, complete the following steps. Make sure to first complete the integration specific deployment steps.

1. Set the Cloud Platform Project in Cloud Shell. Replace `<PROJECT_ID>` with your Cloud Platform project id:
```
gcloud config set project <PROJECT_ID>
```

2. Create Cloud Storage bucket to store Terroform states remotely:

```
PROJECT_ID=$(gcloud config get-value project)

gsutil mb gs://${PROJECT_ID}-tfstate
```

3. (Optional) You may enable Object Versioning to keep the history of your deployments:

```
gsutil versioning set on gs://${PROJECT_ID}-tfstate
```

4. In `~/notification_integration/main.py` edit the `config_map` variables:
```
config_map = {
    'tf-topic-cpu': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': '<YOUR_GOOGLE_CHAT_ROOM_WEBHOOK_URL>'},
    'tf-topic-disk': {
        'service_name': 'google_chat',
        'msg_format': 'card',
        'webhook_url': '<YOUR_GOOGLE_CHAT_ROOM_WEBHOOK_URL>'}
}
```

5. (Optional) If you'd like to not expose your webhook urls in the case of a public repo, skip Step 4 and create a gcs bucket to store the configuration in a json file. Complete the following steps:

Create the GCS bucket
```
gsutil mb gs://gcs_config_bucket_{PROJECT_ID}
```

Upload a json file containing the configuration data named `config_params.json` to the newly created gcs bucket with the format:
You can use ~/notification_integration/config_params.json as a template and update the webhook urls to yours.

6. Retrieve the email for your project's Cloud Build service account:

```
CLOUDBUILD_SA="$(gcloud projects describe $PROJECT_ID --format 'value(projectNumber)')@cloudbuild.gserviceaccount.com"
```

7. Grant the required access to your Cloud Build service account:

```
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/iam.securityAdmin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/storage.admin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/editor
```

8. Trigger a build and deploy to Cloud Run. Replace `<BRANCH>` with the current environment branch:

```
cd ~/notification_integration
```
If you use the in-memory config server, run

```
gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=<BRANCH>
```

If you use the GCS based config server (i.e. you run step 5, instead of step 4), run
```
gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=<BRANCH>,_CONFIG_SERVER_TYPE=gcs
```

9. Create a VM instance to trigger alert policies:

```
gcloud compute instances create {vm_name} --zone={zone}
```

Note that this step uses Terraform to automatically create necessary resources in the Google Cloud Platform project. For more info on what resources are created and managed, refer to the Terraform section below.

10. Create a Pub/Sub notification channel that uses the topic `tf-topic` (which was created by Terraform in the previous step).
11. Add the Pub/Sub channel to an alerting policy by selecting Pub/Sub as the channel type and the channel created in the prior step as the notification channel.
12. Congratulations! Your service is now successfully deployed to Cloud Run and alerts will be forwarded to your provided Google Chat room(s).

### Redeploy

If you've already deployed once manually and want to build and redeploy a new version, do the following:

1.  Checkout the desired GitHub environment branch.

2.  Trigger a build and deploy to Cloud Run. Replace `[BRANCH]` with the current environment branch:

```
cd ~/cloud-monitoring-notification-delivery-integration-sample-code

gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=[BRANCH]
```

## Continuous Deployment

Refer to this solutions guide for instructions on how to setup continuous deployment: TBD

## Running the tests

In order to successfully run unit tests and linter in the section below, setup a virtualenv and install the required dependencies:

```
virtualenv env
source env/bin/activate

pip3 install -r utilities/requirements.txt
```

### Unit Tests

To run unit tests :

```
bash ./scripts/run_tests.sh
```

### Linting

To lint project source code with pylint:

```
bash ./scripts/run_linter.sh
```

## Terraform

Terraform is a HashiCorp open source tool that enables you to predictably create, change, and improve your cloud infrastructure by using code. In this project, Terraform is used to automatically create and manage necessary resources in Google Cloud Platform.

### Resources provisioned with Terraform

Terraform will create the following resources in your cloud project:
* A Cloud Run service called `cloud-run-pubsub-service` to deploy the Flask application
* A Pub/Sub topic called `tf-topic`
* A Pub/Sub push subscription called `alert-push-subscription` with a push endpoint to `cloud-run-pubsub-service`
* A service account with ID `cloud-run-pubsub-invoker` to represent the Pub/Sub subscription identity

In addition, Terraform configures the following authentication policies:
* Enabling Pub/Sub to create authentication tokens in your gcloud project
* Giving the `cloud-run-pubsub-invoker` service account permission to invoke `cloud-run-pubsub-service`
* Adding authentication for `alert-push-subscription` using the `cloud-run-pubsub-invoker` service account

These configurations will be applied automatically on source code changes after connecting Cloud Build with GitHub and when deploying manually.

### Run Terraform Manually

Deployment with Terraform will be automated through source code changes in GitHub. To manually see and apply the changes Terraform makes to your Cloud project resources, do the following:

Navigate to the environment folder and run the following:

Initialize a working directory containing Terraform configuration files:
```
terraform init -backend-config "bucket=$PROJECT_ID-tfstate"
```
Refresh the current Terraform state:
```
terraform refresh -var="project=$PROJECT_ID"
```

To see what changes will be made without applying them yet:
```
terraform plan -var="project=$PROJECT_ID"
``` 

Apply configuration changes:
```
terraform apply -var="project=$PROJECT_ID"
```
When prompted, type `yes` to confirm changes. Once finished, information about the created resources should appear in the output.

## Authors

* **Bing Lin** - [binglin1](https://github.com/binglin1)
* **Dong Wang** - [wdzc](https://github.com/wdzc)

## License

Every file containing source code must include copyright and license
information. This includes any JS/CSS files that you might be serving out to
browsers. (This is to help well-intentioned people avoid accidental copying that
doesn't comply with the license.)

Apache header:

    Copyright 2021 Google LLC

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.