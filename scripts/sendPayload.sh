#!/usr/bin/env bash
set -euo pipefail

# Token comes from .env
TOKEN="$(make --no-print-directory secrets-show)"

curl -v http://127.0.0.1:8000/v1/predict \
  --data @scripts/payload.json \
  -H 'Content-Type: application/json' \
  -H "ML520-API-Key: ${TOKEN}" ${REQUEST_ID+-H "X-Request-Id: ${REQUEST_ID}"}
