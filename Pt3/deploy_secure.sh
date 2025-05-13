#!/bin/bash

# Set variables
PROJECT_ID="computernetworks-450617"
ZONE="us-central1-c"
VM_NAME="fithealth-c3-tdx"
MACHINE_TYPE="c3-standard-4"  # Choose your preferred C3 machine type
IMAGE_FAMILY="ubuntu-2404-lts-amd64"
IMAGE_PROJECT="ubuntu-os-cloud"
DOCKER_IMAGE="ghcr.io/isaactrost/fithealth-secure:latest"

# Create a custom service account if it doesn't exist
CUSTOM_SA_NAME="fithealth-secure-vm-sa"

CUSTOM_SA_EMAIL="$CUSTOM_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts list --project="$PROJECT_ID" | grep -q "$CUSTOM_SA_EMAIL"; then
  gcloud iam service-accounts create "$CUSTOM_SA_NAME" \
    --project="$PROJECT_ID" \
    --display-name="FitHealth VM Service Account"
  # Wait for the service account to be available
  for i in {1..10}; do
    if gcloud iam service-accounts list --project="$PROJECT_ID" | grep -q "$CUSTOM_SA_EMAIL"; then
      break
    fi
    sleep 2
  done
fi

# Now grant roles as before
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CUSTOM_SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CUSTOM_SA_EMAIL" \
  --role="roles/confidentialcomputing.workloadUser"

# Create the VM with Confidential TDX enabled
gcloud compute instances create "$VM_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family="$IMAGE_FAMILY" \
  --image-project="$IMAGE_PROJECT" \
  --confidential-compute-type=TDX \
  --maintenance-policy="TERMINATE" \
  --shielded-secure-boot \
  --min-cpu-platform="Intel Sapphire Rapids" \
  --service-account="$CUSTOM_SA_EMAIL" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --metadata-from-file=startup-script=secure_startup_script.sh

echo "VM $VM_NAME is being created. It will install Docker and launch your FitHealth container automatically."