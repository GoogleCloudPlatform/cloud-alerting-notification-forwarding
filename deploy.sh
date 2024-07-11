#!/bin/bash

echo "One Click Deployment
To deploy the notification channel integration manually, you’ll have to complete the following steps:"

echo "1. Set the Cloud Platform Project in Cloud Shell. Replace <PROJECT_ID> with your Cloud Platform project id which you set as environment variable before running this script:"
echo "gcloud config set project <PROJECT_ID>"
gcloud config set project $PROJECT_ID

echo "2. Enable the Cloud Build Service:"
echo "gcloud services enable cloudbuild.googleapis.com"
gcloud services enable cloudbuild.googleapis.com

echo "3. Enable the Cloud Resource Manager Service:"
echo "gcloud services enable cloudresourcemanager.googleapis.com"
gcloud services enable cloudresourcemanager.googleapis.com

echo "4. Enable the Cloud Service Usage Service:"
echo "gcloud services enable serviceusage.googleapis.com"
gcloud services enable serviceusage.googleapis.com

echo "5. Grant the required permissions to your Cloud Build service account:"
CLOUDBUILD_SA="$(gcloud projects describe $PROJECT_ID --format 'value(projectNumber)')@cloudbuild.gserviceaccount.com"

echo "gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/iam.securityAdmin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/iam.securityAdmin

echo "gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/run.admin

echo "gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/editor"
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:$CLOUDBUILD_SA --role roles/editor

echo "6. Create Cloud Storage bucket to store Terraform states remotely:"
PROJECT_ID=$(gcloud config get-value project)
echo "gsutil mb gs://${PROJECT_ID}-tfstate"
gsutil mb gs://${PROJECT_ID}-tfstate

echo "7. (Optional) You may enable Object Versioning to keep the history of your deployments:"
echo "gsutil versioning set on gs://${PROJECT_ID}-tfstate"
gsutil versioning set on gs://${PROJECT_ID}-tfstate

echo "8. Trigger a build and deploy to Cloud Run:"
echo "gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=main,_DRY_RUN=true,_CONFIG_SERVER_TYPE=in-memory"
gcloud builds submit . --config cloudbuild.yaml --substitutions BRANCH_NAME=main,_DRY_RUN=true,_CONFIG_SERVER_TYPE=in-memory
