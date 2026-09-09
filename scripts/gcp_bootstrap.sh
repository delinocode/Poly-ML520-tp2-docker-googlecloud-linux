#!/usr/bin/env bash
# This script sets up YOUR OWN GCP trial project. Run it once, from your laptop.
#
#   ./scripts/gcp_bootstrap.sh <project-id>
#
# It enables the APIs, creates the Docker repository, creates the service account the
# VM will run as, and opens SSH.
#
# We take the project id as an argument instead of reading `gcloud config`.
# The active project is a machine-wide setting that any command can change.
# A command that creates resources must name where it creates them.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <project-id>" >&2
    exit 1
fi

PROJECT_ID="$1"
REGION="${REGION:-northamerica-northeast1}"
AR_REPO="${AR_REPO:-ml520}"
VM_SA="ml520-vm"
SA_EMAIL="${VM_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

enable_apis() {
    echo "Enabling APIs..."
    gcloud services enable \
        compute.googleapis.com \
        artifactregistry.googleapis.com \
        --project="$PROJECT_ID"
}

create_docker_repository() {
    if gcloud artifacts repositories describe "$AR_REPO" \
        --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "repository ${AR_REPO} already exists"
        return
    fi
    gcloud artifacts repositories create "$AR_REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --description="ML520 images" \
        --project="$PROJECT_ID"
}

create_vm_service_account() {
    if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
        gcloud iam service-accounts create "$VM_SA" \
            --display-name="ML520 VM" \
            --project="$PROJECT_ID"
    fi
    # Allow the virtual machine to READ from Artifact Registry
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/artifactregistry.reader" \
        --condition=None >/dev/null
}

open_ssh() {
    if gcloud compute firewall-rules describe allow-ssh --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "firewall rule allow-ssh already exists"
        return
    fi
    # The default VPC already ships a `default-allow-ssh` rule that does the same
    # thing. We create our own anyway, so that the rules of this project are yours to
    # read and to change: `gcloud compute firewall-rules list` should be enough to
    # explain how anyone reaches your machine.
    #
    # 0.0.0.0/0 is the whole internet, and that is a deliberate course setting: it is
    # what lets you use plain ssh, scp and rsync instead of a tunnel. Password login is
    # off on this image, so only your key gets in. Read `journalctl -u ssh` after a day
    # anyway and count what knocked - then reread this comment.
    #
    # Port 8000 is NOT opened. You reach the service through an SSH tunnel.
    gcloud compute firewall-rules create allow-ssh \
        --allow=tcp:22 \
        --source-ranges=0.0.0.0/0 \
        --description="SSH from anywhere - ML520 course setting, see TP2" \
        --project="$PROJECT_ID"
}

configure_local_docker() {
    # We name the host because a bare `gcloud auth configure-docker` only configures
    # the legacy gcr.io hosts.
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
}

enable_apis
create_docker_repository
create_vm_service_account
open_ssh
configure_local_docker

echo
echo "project:          ${PROJECT_ID}"
echo "region:           ${REGION}"
echo "image repository: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
echo "VM identity:      ${SA_EMAIL}"
