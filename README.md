# Sample Code for the Cloud Monitoring Notification Delivery Integration Guide

**This is not an officially supported Google product.**

This repository provides examples of how a Google Cloud user can forward **[notifications](https://cloud.google.com/monitoring/alerts#how_does_alerting_work)** to third-party integrations not officially supported as **[notification options](https://cloud.google.com/monitoring/support/notification-options)**. The two provided examples forward notifications to a Philips Hue smart bulb and a Jira server. Each example accomplishes this through the use of a Flask server running on Cloud Run which recieves monitoring notifications through Cloud Pub/Sub push messages and then parses and delivers them to a third party service.

The sample code in this repository is referenced in this **[Cloud Community tutorial](https://cloud.google.com/community/tutorials/delivering-cloud-monitoring-notifications-to-third-party-services)**. 

## Folder Structure

    .
    ├── .github/workflows
    ├── docs
    ├── environments                      # Terraform configurations for each environment
    │   ├── prod
    │   └── dev
    ├── jira_integration_example          # Jira Integration
    │   ├── utilities
    │   ├── tests                         # Unit and integration tests
    │   ...
    ├── modules                           # Terraform modules
    ├── philips_hue_integration_example   # Philips Hue Integration
    │   ├── utilities
    │   ├── tests                         # Unit tests
    │   ...
    ├── scripts                           # Scripts for testing and authentication
    .
    .
    .
    └── cloudbuild.yaml                   # Build configuration file

## Setup

1.  Create a [new Google Cloud Platform project from the Cloud
    Console](https://console.cloud.google.com/project) or use an existing one.

2.  Click the "Open in Cloud Shell" button below to clone and open this repository on Cloud Shell.

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgoogleinterns%2Fcloud-monitoring-notification-delivery-integration-sample-code)

3.  Set the Cloud Platform project in Cloud Shell. Replace `[PROJECT_ID]` with your Cloud Platform project id:

```
gcloud config set project [PROJECT_ID]
```

4.  (Optional) In order to successfully run unit tests and linter in the section below, setup a virtualenv and install the required dependencies:

```
virtualenv env
source env/bin/activate

pip3 install -r philips_hue_integration_example/requirements.txt
pip3 install -r jira_integration_example/requirements.txt
pip3 install -r scripts/requirements.txt
```

## Manual Deployment

To deploy either the Philips Hue integration or Jira integration for the first time manually, complete the following steps. Make sure to first complete the integration specific deployment steps (part 1), then complete the deployment steps for all integrations (part 2). However if you are redeploying, complete the steps in the redeploying section.

### Part 1: Integration Specific Deployment Steps

#### Philips Hue Integration
1. Store your Philips Hue bridge IP address as `philips_ip` and username as `philips_username` in [Secret Manager](https://cloud.google.com/secret-manager/docs/quickstart#create_and_access_a_secret_version).
2. Checkout the desired GitHub environment branch (`dev` or `prod`).
4. Edit the `cloudbuild.yaml` configuration file to build a Philips Hue Docker image. Make sure the following line is set in the `build docker image` step:

```
args: ['build', '--build-arg', 'PROJECT_ID=$PROJECT_ID', '--tag', 'gcr.io/$PROJECT_ID/${_IMAGE_NAME}', './philips_hue_integration_example']
```

#### Jira Integration
1. Store your Jira Server URL as `jira_url` and Jira project as `jira_project` in [Secret Manager](https://cloud.google.com/secret-manager/docs/quickstart#create_and_access_a_secret_version).
2. Setup Jira OAuth to be used to authenticate the Jira client in the Cloud Run service. Replace `[JIRA_URL]` with your Jira Server URL:

```
python3 jira_oauth_setup_script.py --gcp_project_id=$PROJECT_ID [JIRA_URL]
```

(Note, this script prompts you to complete some steps manually)

3. Checkout the desired GitHub environment branch (`dev` or `prod`).
4. Edit the `cloudbuild.yaml` configuration file to build a Jira Docker image. Make sure the following line is set in the `build docker image` step:

```
args: ['build', '--build-arg', 'PROJECT_ID=$PROJECT_ID', '--tag', 'gcr.io/$PROJECT_ID/${_IMAGE_NAME}', './jira_hue_integration_example']
```

### Part 2: Deployment Steps for all Integrations
1. Create Cloud Storage bucket:

```
PROJECT_ID=$(gcloud config get-value project)

gsutil mb gs://${PROJECT_ID}-tfstate
```

2. You may optionally enable Object Versioning to keep the history of your deployments:

```
gsutil versioning set on gs://${PROJECT_ID}-tfstate
```

3. Retrieve the email for your project's Cloud Build service account:

```
CLOUDBUILD_SA="$(gcloud projects describe $PROJECT_ID --format 'value(projectNumber)')@cloudbuild.gserviceaccount.com"
```

4. Grant the required access to your Cloud Build service account:

```
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/iam.securityAdmin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/storage.admin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/editor
```

5. To allow the Cloud Run service to access secrets in Secret Manager, grant the Compute Engine default service account the Secret Manager Secret Accessor role. Replace `[PROJECT_NUMBER]` with the Cloud project number:

```
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com --role roles/secretmanager.secretAccessor
```

6. Trigger a build and deploy to Cloud Run. Replace `[BRANCH]` with the current environment branch:

```
cd ~/cloud-monitoring-notification-delivery-integration-sample-code

gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=[BRANCH]
```

Note that this step uses Terraform to automatically create necessary resources in the Google Cloud Platform project. For more info on what resources are created and managed, refer to the Terraform section below.

7. Create a Pub/Sub notification channel that uses the topic `tf-topic` (which was created by Terraform in the previous step).
8. Add the Pub/Sub channel to an alerting policy by selecting Pub/Sub as the channel type and the channel created in the prior step as the notification channel.
9. Congratulations! Your service is now successfully deployed to Cloud Run and alerts will be forwarded to either the Philips Hue light bulb or Jira server.

### Redeploy

If you've already deployed once manually and want to build and redeploy a new version, do the following:

1.  Checkout the desired GitHub environment branch (dev or prod).

2.  Trigger a build and deploy to Cloud Run. Replace `[BRANCH]` with the current environment branch:

```
cd ~/cloud-monitoring-notification-delivery-integration-sample-code

gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=[BRANCH]
```

## Continuous Deployment

Refer to this solutions guide for instructions on how to setup continuous deployment: TBD

## Running the tests

In order to successfully run these tests, make sure you have successfully setup virtualenv and installed the required dependencies as specified in the "Setup" section above.

### Unit Tests

To run unit tests for Philips Hue and Jira integrations:

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

Navigate to the desired environment folder (`environments/dev` or `environments/prod`) and run the following:

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

* **Ruben Hambardzumyan** - [rubenh00](https://github.com/rubenh00)
* **April Xie** - [aprill1](https://github.com/aprill1)

See also the list of [contributors](https://github.com/googleinterns/cloud-monitoring-notification-delivery-integration-sample-code/contributors) who participated in this project.

## License

Every file containing source code must include copyright and license
information. This includes any JS/CSS files that you might be serving out to
browsers. (This is to help well-intentioned people avoid accidental copying that
doesn't comply with the license.)

Apache header:

    Copyright 2020 Google LLC

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
