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
#
# A sample PY3 script that automatically setups a Cloud Pubsub + Google Chat
# integration demo in a new project.
# It will set the given project as the default gcloud project, enable all the
# necessary services in the given project, set up the Google storage (GCS) 
# bucket to save the Terraform remote state,  set up the IAM policies for 
# the Cloud Build service account, and then trigger the Cloud Build. 
#
# To run this script, make sure that 
#   a) Python 3 (3.5 or newer) and Google Cloud SDK are installed.
#      See https://cloud.google.com/sdk/docs/install.
#   b) A cloud billing account is set for the given project.
#      See https://cloud.google.com/billing/docs/how-to/modify-project 
import getopt
import sys
import subprocess
import time

from typing import Dict, Set, Optional, Text

_HELP_INFO = (
    'Please run the deploy command as the following: \n'
    'python3 deploy.py -p <project_id> -b <git_branch> -c <config_server_name>. \n'
    'E.g. python3 deploy.py -p my_project -b main -c gcs \n'
    'The command line options: \n'
    '  -p: The ID of the GCP project in which to deploy the notification integration. \n'
    '  -b: The git branch name. The default value is "main"\n'
    '  -c: The configuration server type. Currently it supports "gcs" and "in-memory".\n'
    '      The default value is "in-memory"\n'
    'You can also run "python3 deploy.py -h" to see this help information.'
)

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
    raise
  else:
    print('Sucessfully completed the command: {}'.format(cmd))     
    return result  

def _SetProjectForInvocation(project_id: Text):
  """Sets the given project ID as the one to use for this invocation."""
  gcloud_cmd = 'gcloud config set project {project}'.format(project=project_id)
  err_msg = 'Failed to set the project ID for this invocation: {}'.format(
    project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg)

def _EnableCloudBuildService(project_id: Text):
  """Enables the Google Cloud Build service."""
  gcloud_cmd = 'gcloud services enable cloudbuild.googleapis.com'
  err_msg = 'Failed to enable the Cloud Build service for the project: {}'.format(
    project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg)

def _EnableCloudResourceManagerService(project_id: Text):
  """Enables the Google Cloud Resource Manager serive."""
  gcloud_cmd = 'gcloud services enable cloudresourcemanager.googleapis.com'
  err_msg = ('Failed to enable the Cloud Resource Manager service for the '
             'project: {}').format(project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg, wait_before_return_sec=5)

def _EnableCloudServiceUsageService(project_id: Text):
  """Enables the Google Cloud Service Usage serive."""
  gcloud_cmd = 'gcloud services enable serviceusage.googleapis.com'
  err_msg = ('Failed to enable the Cloud Service Usage service for the '
             'project: {}').format(project_id)
  _RunGcloudCommand(gcloud_cmd, err_msg, wait_before_return_sec=5)

def _EnableComputeEngineService(project_id: Text):
  """Enables the Google Cloud Compute Engine serive."""
  gcloud_cmd = 'gcloud services enable compute.googleapis.com'
  err_msg = ('Failed to enable the Cloud Compute Engine service for the '
             'project: {}').format(project_id)
  # Enabling the compute engine service takes time, so wait for 15 seconds.           
  _RunGcloudCommand(gcloud_cmd, err_msg, wait_before_return_sec=15)

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

def _TriggerCloudBuild(branch: Text, dry_run: bool = False, config_server_type: Text = 'in-memory'):
  """Triggers the Cloud Build to run the local cloudbuild.yaml file."""
  # The config_server_type can be in-memory or gcs. If it is set to gcs, don't forget to create
  # a GCS bucket naming 'gcs_config_bucket_{project_id}' and upload the config file config_params.json
  # to the bucket before running the script. You also need to grant read permission to the Cloud Run
  # default service account PROJECT_NUMBER-compute@developer.gserviceaccount.com, see 
  # https://cloud.google.com/run/docs/configuring/service-accounts.
  gcloud_cmd = ('gcloud builds submit . --config cloudbuild.yaml '
                '--substitutions BRANCH_NAME={branch},_DRY_RUN={dry_run},_CONFIG_SERVER_TYPE={config_server_type}').format(
                  branch=branch, dry_run=dry_run, config_server_type=config_server_type)

  err_msg = 'Failed to trigger the cloud build for cloudbuild.yaml'
  _RunGcloudCommand(gcloud_cmd, err_msg)

def _CreateVmInstance(project_id: Text, vm_name: Text, zone: Text):
  """Creates a VM instance."""  
  gcloud_cmd = 'gcloud compute instances create {vm_name} --zone={zone}'.format(
    vm_name=vm_name, zone=zone)
  err_msg = 'Failed to create a VM instance in {}'.format(zone)
  _RunGcloudCommand(gcloud_cmd, err_msg)

def main(argv: Dict[Text, Text]):
  # Set the default gcloud project to a new project. Make sure the billing account is set.
  project_id = ''
  branch = 'main'  # The Git branch to use.
  config_server_type = 'in-memory'

  try:
     opts, args = getopt.getopt(argv, 'hp:b:c:',['project_id=', 'branch=', 'config_server_type='])
  except BaseException as e:
     print(f'Failed to extract the command line arguments: {e}')
     print(_HELP_INFO)
     raise
  for opt, arg in opts:
     if opt == '-h':
       print(_HELP_INFO)
       return
     elif opt in ("-p", "--project_id"):
       project_id = arg
     elif opt in ("-b", "--branch"):
       branch = arg
     elif opt in ("-c", "--config_server_type"):
       config_server_type = arg
     else:
       print(_HELP_INFO)
       raise ValueError(f'Unkonwn command line argument: {opt}')

  print(f'Starting the deployment: project_id={project_id}, branch={branch}, config_server_type={config_server_type}')
  return
  print('---- Step 1: Set up the default gcloud project for the current invocation: {}'.format(project_id))
  _SetProjectForInvocation(project_id)

  # Enable the Cloud Build Service, which is needed to trigger Cloud Build.  
  print('---- Step 2: Enable the Cloud Build Service')
  _EnableCloudBuildService(project_id)

  # Enable the Google Cloud Resource Manager serive, which is needed to manage
  # resources in Terraform.
  print('---- Step 3: Enable the Cloud Resource Manager Service')
  _EnableCloudResourceManagerService(project_id)

  # Enable the Google Cloud Service Usage serive, which is needed to
  # enable/disable services in Terraform.
  print('---- Step 4: Enable the Cloud Service Usage Service')
  _EnableCloudServiceUsageService(project_id)

  # Grants necessary roles to the cloud build SA so it can run Terraform scripts.
  print('---- Step 5: Grant the Cloud Run service account necessary roles')
  cloud_build_sa_roles = set(
    ['roles/editor', 'roles/iam.securityAdmin', 'roles/run.admin'])
  _GrantRolesToCloudBuildSa(project_id, cloud_build_sa_roles)

  # Setups the GCS bucket for Terraform to save states remotely.
  print('---- Step 6: Set up a GCS bucket for Terraform to save states remotely')
  _SetupTfRemoteState(project_id)

  # Manully trigger the Cloud Build.
  print('---- Step 7: Manually trigger the Cloud Build: branch={}, config_server_type={}'.format(branch, config_server_type))
  _TriggerCloudBuild(branch, config_server_type=config_server_type)

  # Optional: Create a VM instance to trigger the alerting polices created with Terraform.
  # If you don't want to automatically trigger the created alert policies, you can remove
  # this step.
  print('---- Step 8: Create a VM instance to trigger alert polices')
  print('----   Step 8.1: Enable the Compute Engine service')
  _EnableComputeEngineService(project_id)
  print('----   Step 8.2: Create a VM instance')
  vm_name = 'cloud-alerting-test-vm'
  zone = 'us-east1-b'
  _CreateVmInstance(project_id, vm_name, zone)
  print('**** Congratulations, you successfully finished the cloud alerting integration demo setup, '
        'please wait for your first alerting notification patiently!')


if __name__ == '__main__':
  main(sys.argv[1:])
