#!/usr/bin/env bash
# Hammer /v1/predict with siege.
set -euo pipefail

# Token comes from .env
TOKEN="$(make --no-print-directory secrets-show)"

siege -H 'Content-Type: application/json' -H "ML520-API-Key: ${TOKEN}" \
  'http://127.0.0.1:8000/v1/predict POST < scripts/payload.json'
