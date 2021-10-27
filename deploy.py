#!/usr/bin/python

import subprocess
import time
project_id='oss-test-1021-1'
subprocess.run(['gcloud config set project {project}'.format(project=project_id)], shell=True)
subprocess.run(['gcloud services enable cloudbuild.googleapis.com'], shell=True)
time.sleep(10)
subprocess.run(['gcloud services enable cloudresourcemanager.googleapis.com'], shell=True)
time.sleep(10)
subprocess.run(['gcloud services enable serviceusage.googleapis.com'], shell=True)
time.sleep(10)
subprocess.run(['gcloud services enable cloudmonitoring.googleapis.com'], shell=True)
time.sleep(10)
result = subprocess.run(['gcloud projects describe {project} --format "value(projectNumber)"'.format(project=project_id)], shell=True, capture_output=True, text=True)
cloudbuild_sa = result.stdout.strip() + '@cloudbuild.gserviceaccount.com'
subprocess.run(['gcloud projects add-iam-policy-binding {project} --member serviceAccount:{cloudbuild} --role roles/editor'.format(project=project_id, cloudbuild=cloudbuild_sa)], shell=True)
subprocess.run(['gcloud projects add-iam-policy-binding {project} --member serviceAccount:{cloudbuild} --role roles/iam.securityAdmin'.format(project=project_id, cloudbuild=cloudbuild_sa)], shell=True)
subprocess.run(['gcloud projects add-iam-policy-binding {project} --member serviceAccount:{cloudbuild} --role roles/run.admin'.format(project=project_id, cloudbuild=cloudbuild_sa)], shell=True)

subprocess.run(['gsutil mb gs://{project}-tfstate'.format(project=project_id)], shell=True)
subprocess.run(['gsutil versioning set on gs://{project}-tfstate'.format(project=project_id)], shell=True)
branch_name='master'
subprocess.run(['gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME={branch}'.format(branch=branch_name)], shell=True)

# subprocess.run(['gcloud beta builds triggers create cloud-source-repositories \\
#     --repo="oss-gchat-handler" \\
#     --branch-pattern="master"'])

