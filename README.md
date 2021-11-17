# Sample Code for the Cloud Monitoring Notification Delivery Integration Guide

**This is not an officially supported Google product.**

This repository provides examples of how a Google Cloud user can forward **[notifications](https://cloud.google.com/monitoring/alerts#how_does_alerting_work)** to third-party integrations not officially supported as **[notification options](https://cloud.google.com/monitoring/support/notification-options)**. The provided example forward notifications to a Google chat room. The example accomplishes this through the use of a Flask server running on Cloud Run which recieves monitoring notifications through Cloud Pub/Sub push messages and then parses and delivers them to a third party service.

The sample code in this repository is referenced in this **[Cloud Community tutorial](new blog link)**. 

## Folder Structure

    .
    ├── .github/workflows
    ├── docs
    ├── environments                      # Terraform configurations for each environment
    │   ├── prod
    ├── modules                           # Terraform modules
    ├── gchat_integration                 # Google Chat Integration
    │   ├── utilities
    │   ├── tests                         # Unit tests
    │   ...
    ├── scripts                           # Scripts for testing
    .
    .
    .
    └── cloudbuild.yaml                   # Build configuration file

## Setup

1.  Create a [new Google Cloud Platform project from the Cloud
    Console](https://console.cloud.google.com/project) or use an existing one.

2. Be sure to [enable billing](https://cloud.google.com/billing/docs/how-to/modify-project) in your new GCP project.

3. Click the "Open in Cloud Shell" button below to clone and open this repository on Cloud Shell.

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](github link)

## One Button / Automatic deployment

To deploy the Gchat integration for the first time automatically, we've provided a script `deploy.py` that will handle a majority of the required actions for deployment. Complete the following steps before running the script.

1. Set the `project_id` variable in `deploy.py`
```
def main():
  # Set the default gcloud project to a new project. Make sure the billing account is set.
  project_id = 'wdzc-oss-1107-02'
```

2. (Optional) If you'd like to edit the VM instance that's created in the deployment script you can edit the following:
```
  _EnableComputeEngineService(project_id)
  print('----   Step 8.2: Create a VM instance')
  vm_name = 'cloud-alerting-test-vm'
  zone = 'us-east1-b'
  ```

3. Run the script with the following command:
  ```
  python3 deploy.py
  ```

4. To complete the deployment, you will need to upload a json file named `channel_name_to_url_map.json` to the created bucket named `{project_id}-tfstate`. The json file should contain the webhook url(s) for notifications to be forwarded to and it should be in the following format:
```
{"topic-name": "webhook-url",
 "topic-name": "webhook-url" 
}
```

## Manual Deployment

To deploy the Google chat integration manually, complete the following steps. Make sure to first complete the integration specific deployment steps.

1. Set the Cloud Platform Project in Cloud Shell. Replace `[PROJECT_ID]` with your Cloud Platform project id:
```
gcloud config set project [PROJECT_ID]
```

2. Create Cloud Storage bucket:

```
PROJECT_ID=$(gcloud config get-value project)

gsutil mb gs://${PROJECT_ID}-tfstate
```

3. You may optionally enable Object Versioning to keep the history of your deployments:

```
gsutil versioning set on gs://${PROJECT_ID}-tfstate
```

5. Create Cloud Storage bucket for your webhook url(s):

```
gsutil mb gs://url_config_{PROJECT_ID}
```

6. Upload json containing the webhook url(s) to the `url_config_{PROJECT_ID}` bucket

```
{"topic-name": "webhook-url",
 "topic-name": "webhook-url" 
}
```
4. Retrieve the email for your project's Cloud Build service account:

```
CLOUDBUILD_SA="$(gcloud projects describe $PROJECT_ID --format 'value(projectNumber)')@cloudbuild.gserviceaccount.com"
```

5. Grant the required access to your Cloud Build service account:

```
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/iam.securityAdmin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/storage.admin

gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/editor
```

6. Trigger a build and deploy to Cloud Run. Replace `[BRANCH]` with the current environment branch:

```
cd ~/gchat_integration

gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=[BRANCH]
```

7. Create a VM instance to trigger alert policies:

```
gcloud compute instances create {vm_name} --zone={zone}
```

Note that this step uses Terraform to automatically create necessary resources in the Google Cloud Platform project. For more info on what resources are created and managed, refer to the Terraform section below.

7. Create a Pub/Sub notification channel that uses the topic `tf-topic` (which was created by Terraform in the previous step).
8. Add the Pub/Sub channel to an alerting policy by selecting Pub/Sub as the channel type and the channel created in the prior step as the notification channel.
9. Congratulations! Your service is now successfully deployed to Cloud Run and alerts will be forwarded to your provided Google Chat room(s).

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

In order to successfully run these tests, make sure you have successfully setup virtualenv and installed the required dependencies as specified in the "Setup" section above.

In order to successfully run unit tests and linter in the section below, setup a virtualenv and install the required dependencies:

```
virtualenv env
source env/bin/activate

pip3 install -r scripts/requirements.txt
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