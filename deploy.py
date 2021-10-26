#!/usr/bin/python

import subprocess
subprocess.run(['gcloud services enable cloudbuild.googleapis.com'],shell=True)
project_id='oss-test-1021-2'
# # project_id='oss-test-1-324219'
branch_name='master'
subprocess.run(['gcloud config set project {project}'.format(project=project_id)], shell=True)
subprocess.run(['gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME={branch}'.format(branch=branch_name)], shell=True)

# subprocess.run(['gcloud beta builds triggers create cloud-source-repositories \\
#     --repo="oss-gchat-handler" \\
#     --branch-pattern="master"'])

