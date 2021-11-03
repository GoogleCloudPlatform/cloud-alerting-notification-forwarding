# Sample Code for Cloud Alerting PubSub Notification Channel Integration Guide

**This is not an officially supported Google product.**

This repository provides examples of how a Google Cloud user can forward **[notifications](https://cloud.google.com/monitoring/alerts#how_does_alerting_work)** to third-party integrations not officially supported as **[notification options](https://cloud.google.com/monitoring/support/notification-options)**. 

TBD

## Folder Structure

<TBD>

## Setup

<TBD>

## Manual Deployment

<TBD>

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

<TBD>

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

<TBD>

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
