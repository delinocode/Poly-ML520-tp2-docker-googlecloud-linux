#!/usr/bin/env bash
# This is the only way to start the service.
#
#   ./scripts/entrypoint.sh
#
set -euo pipefail

# Move to the project root so the paths below work no matter where the repo lives.
cd "$(dirname "$0")/.."

# ${VAR:-default} means "use VAR, or this default if VAR is empty or unset".
# Every setting gets a default here.
# You configure a container by overriding these defaults from the environment.
PORT="${PORT:-8000}"
BIND_ADDR="${BIND_ADDR:-0.0.0.0}"
WORKERS="${WORKERS:-2}"
MODEL_PATH="${ML520_SERVING__MODEL_PATH:-out/models/model.joblib}"

# NOTE(LAB): This would be done anyway with pydantic-settings, but just roll with it :)
require_token() {
    # TODO(LAB): refuse to start when ML520_SECURITY__API_TOKEN is empty or unset.
    #            The message must name the variable: whoever reads it is looking at
    #            `journalctl` output, not at this file.
    :
}

# NOTE(LAB): This would be done anyway with pydantic-settings, but just roll with it :)
require_model() {
    # TODO(LAB): refuse to start when the model artifact is not where MODEL_PATH says.
    :
}

require_token
require_model

# TODO(LAB): start gunicorn with `exec`, binding to ${BIND_ADDR}:${PORT} with
#            $WORKERS uvicorn workers. `make serve` shows the flags.
exec .venv/bin/gunicorn --workers "$WORKERS" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "${BIND_ADDR}:${PORT}" \
    inferapi.serve:app
