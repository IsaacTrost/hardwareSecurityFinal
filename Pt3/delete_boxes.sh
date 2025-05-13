#!/bin/bash

# Set variables
PROJECT_ID="computernetworks-450617"
ZONE="us-central1-c"
VM_NAMES=("fithealth-c3-tdx" "fithealth-insecure")

for VM_NAME in "${VM_NAMES[@]}"; do
    # Delete the VM
    gcloud compute instances delete "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --quiet

    echo "VM $VM_NAME has been deleted from project $PROJECT_ID in zone $ZONE."
done
