#!/usr/bin/python3
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# A sample PY3 script that automatically setups a Cloud Pubsub + Google Chat
# integration demo in a new project.
# To run this script, make sure that 
#   a) Python 3 (3.5 or newer) and Google Cloud SDK are installed.
#      See https://cloud.google.com/sdk/docs/install.
#   b) A cloud billing account is set for the given project.
#      See https://cloud.google.com/billing/docs/how-to/modify-project 
import subprocess
import time

from typing import Set, Optional, Text

def _RunGcloudCommand(cmd: Text, err_msg: Text, wait_before_return_sec: int = 0
) -> subprocess.CompletedProcess:
  """Runs the given gcloud command and outputs the error message if failed.

  Args:
    cmd: Gcloud command to run.
    err_msg: The error message to print if the execution fails.
    wait_before_return_sec: How long it waits after completing the command,
      in seconds. This is to ensure the excution result is populated.
  Returns:
    A subprocess.CompletedProcess instance with the execution result.
  Raises:
    Any Exception raised during the command run.
  """
  try:
    # If the exit code is non-zero, it will fail.  
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            check=True)
    if wait_before_return_sec > 0:
      time.sleep(wait_before_return_sec)
  except subprocess.CalledProcessError as e:    
    print(err_msg)
    print(e.output)
    print(e.stderr)
    raise
  except BaseException as e:
    print(err_msg)
    print('Exception raised {}'.format(e))
    print(e)
    raise
  else:
    print('Sucessfully completed the command: {}'.format(cmd))     
    return result  

def _SetProjectForInvocation(project_id: Text):
  """Set the given project ID as the one to use for this invocation."""
  gcloud_cmd = 'gcloud config set project {project}'.format(project=project_id)
  err_msg = 'Failed to set the project ID for this invocation: {}'.format(
    project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg)

def _EnableCloudBuildService(project_id: Text):
  """Enable the Google Cloud Build service."""
  gcloud_cmd = 'gcloud services enable cloudbuild.googleapis.com'
  err_msg = 'Failed to enable the Cloud Build service for the project: {}'.format(
    project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg)

def _EnableCloudResourceManagerService(project_id: Text):
  """Enable the Google Cloud Resource Manager serive."""
  gcloud_cmd = 'gcloud services enable cloudresourcemanager.googleapis.com'
  err_msg = ('Failed to enable the Cloud Resource Manager service for the '
             'project: {}').format(project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg, wait_before_return_sec=10)

def _EnableCloudServiceUsageService(project_id: Text):
  """Enable the Google Cloud Service Usage serive."""
  gcloud_cmd = 'gcloud services enable serviceusage.googleapis.com'
  err_msg = ('Failed to enable the Cloud Service Usage service for the '
             'project: {}').format(project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg, wait_before_return_sec=10)

def _GetProjectNumberFromId(project_id: Text) -> Text:
  """Converts a project Id into its project number."""
  gcloud_cmd = ('gcloud projects describe {project} --format '
                '"value(projectNumber)"').format(project=project_id)
  err_msg = 'Failed to get the project number of the project {}'.format(
    project_id)
  result = _RunGcloudCommand(gcloud_cmd, err_msg)
  return result.stdout.strip()

def _GrantRolesToCloudBuildSa(project_id: Text, roles: Set[Text]):
  """Grants roles to the default Cloud Build service account."""    
  project_number = _GetProjectNumberFromId(project_id)
  cloudbuild_sa = '{project_number}@cloudbuild.gserviceaccount.com'.format(
    project_number=project_number)

  for role in roles:
    gcloud_cmd = ('gcloud projects add-iam-policy-binding {project_id} --member '
                  'serviceAccount:{cloudbuild} --role {role}').format(
                    project_id=project_id, cloudbuild=cloudbuild_sa, role=role)
    err_msg = ('Failed to grant role {role} to the Cloud Build service account '
               '{cloudbuild_sa}').format(role=role, cloudbuild_sa=cloudbuild_sa)
    _RunGcloudCommand(gcloud_cmd, err_msg)

def _SetupTfRemoteState(project_id: Text):
  """Setups a GCS bucket to store Terraform states remotely."""
  # Create a GCS bucket with the name of "<project_id>-tfstate".
  gcs_bucket_name = '{project_id}-tfstate'.format(project_id=project_id)
  gcloud_cmd = 'gsutil mb gs://{gcs_bucket_name}'.format(
    gcs_bucket_name=gcs_bucket_name)
  err_msg = 'Failed to create the GCS bucket {gcs_bucket_name}'.format(
    gcs_bucket_name=gcs_bucket_name)
  _RunGcloudCommand(gcloud_cmd, err_msg)
  # Enable the versioning of the GCS bucket.
  gcloud_cmd = 'gsutil versioning set on gs://{gcs_bucket_name}'.format(
    gcs_bucket_name=gcs_bucket_name)
  err_msg = ('Failed to enable versioning of the GCS bucket '
             '{gcs_bucket_name}').format(gcs_bucket_name=gcs_bucket_name)
  _RunGcloudCommand(gcloud_cmd, err_msg)

def _TriggerCloudBuild(branch: Text):
  """Triggers the Cloud Build to run the local cloudbuild.yaml file."""
  gcloud_cmd = ('gcloud builds submit . --config cloudbuild.yaml '
                '--substitutions BRANCH_NAME={branch}').format(
                  branch=branch)
  err_msg = 'Failed to trigger the cloud build for cloudbuild.yaml'
  _RunGcloudCommand(gcloud_cmd, err_msg)

# Set to a new project. Make sure the billing account is set.
project_id='wdzc-oss-test-2'
_SetProjectForInvocation(project_id)

# Enable the Cloud Build Service, which is needed to trigger Cloud Build.  
_EnableCloudBuildService(project_id)

# Enable the Google Cloud Resource Manager serive, which is needed to manage
# resources in Terraform.
_EnableCloudResourceManagerService(project_id)

# Enable the Google Cloud Service Usage serive, which is needed to
# enable/disable services in Terraform.
_EnableCloudServiceUsageService(project_id)

# Grants necessary roles to the cloud build SA so it can run Terraform scripts. 
cloud_build_sa_roles = set(
  ['roles/editor', 'roles/iam.securityAdmin', 'roles/run.admin'])
_GrantRolesToCloudBuildSa(project_id, cloud_build_sa_roles)

# Setups the GCS bucket for Terraform to save states remotely.
_SetupTfRemoteState(project_id)

# Manully trigger the Cloud Build.
branch = 'master'  # The Git branch to use.
_TriggerCloudBuild(branch)