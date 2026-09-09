#!/usr/bin/env bash
# Copy this project onto the VM.
#
#   ./scripts/vm_sync.sh mlops@ml520-vm.northamerica-northeast1-b.my-project
#
# Run it from your laptop, from the project root, every time you change something.
# rsync compares both sides first and sends only what differs, so the second run is
# fast even though the first one was not.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <user@host>" >&2
    exit 1
fi

TARGET="$1"
VM_DIR="${VM_DIR:-/opt/inferapi}"

# What travels is a decision, not a default. rsync does not read .gitignore: it sends
# whatever you point it at, so every line below is deliberate.
#   .git/          history belongs on your laptop and in the bundle you hand in
#   .venv/         half a gigabyte of binaries built for YOUR machine, not for Ubuntu
#   .env           the token stays here; you retype it on the VM by hand
#   out/           the VM trains its own model and writes its own logs
#   dataset.csv    only the parquet is read; the CSV is 6 MB of nothing useful
# `data/dataset.parquet` is gitignored and travels anyway: the VM has to train.
#
# Compare this list with .dockerignore. They answer the same question and disagree.

# -a keeps the executable bit, which entrypoint.sh needs to be startable by systemd.
# -z compresses in flight, -h prints sizes a human can read.
# The trailing slash on `./` means "the contents of this directory", not "this
# directory": without it you would get ${VM_DIR}/lab2_starter/.
rsync -azh --info=progress2 \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='.env' \
    --exclude='out/' \
    --exclude='data/dataset.csv' \
    --exclude='notebooks/' \
    --exclude='reports/' \
    --exclude='**/__pycache__/' \
    --exclude='.ruff_cache/' \
    --exclude='.pytest_cache/' \
    ./ "${TARGET}:${VM_DIR}/"

echo "synced to ${TARGET}:${VM_DIR}"
