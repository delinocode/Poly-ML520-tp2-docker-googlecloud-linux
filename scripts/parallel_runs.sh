#!/usr/bin/env bash
# Train one model per hyperparameter combination.
# Each run writes its own log file.
#
#   ./scripts/parallel_runs.sh
#
# This is an academic exercise. A real hyperparameter search uses a tool that picks
# the next point to try (Optuna, Ray Tune, a job scheduler). The bash loop below has
# no such logic. It tries every combination, including the useless ones.

set -euo pipefail

# Move to the project root so the paths below work no matter where the repo lives.
cd "$(dirname "$0")/.."

# These are bash arrays. The loops at the bottom expand them with "${NAME[@]}".
N_ESTIMATORS=(100 200 400)
MAX_DEPTHS=(4 8 16)

RUN_LOG_DIR="out/runs"
MODEL_DIR="out/models/runs"
SUMMARY="out/logs/parallel_runs.log"

run_one() {
    local n_estimators="$1"
    local max_depth="$2"
    local name="n${n_estimators}_d${max_depth}"
    local logfile="${RUN_LOG_DIR}/${name}.log"
    local started
    started="$(date +%s)"

    local exit_code=0

    # `2>&1` sends stderr down the same redirection as stdout.
    # `set -e` would end the whole script on a failed run. `|| exit_code=$?` catches
    # the failure instead, so one bad combination does not stop the other eight.
    .venv/bin/inferapi train \
        --n-estimators "$n_estimators" \
        --max-depth "$max_depth" \
        --output "${MODEL_DIR}/${name}.joblib" \
        --overwrite \
        >"$logfile" 2>&1 || exit_code=$?

    # Write one value per line so a later `grep` picks a single field out of the file.
    # The braces group the echos. That way the redirection appears once, not six times.
    {
        echo "run_name=${name}"
        echo "n_estimators=${n_estimators}"
        echo "max_depth=${max_depth}"
        echo "duration_s=$(($(date +%s) - started))"
        echo "exit_code=${exit_code}"
        echo "logfile=${logfile}"
    } >>"$SUMMARY"
}

report_failures() {
    if grep 'exit_code=' "$SUMMARY" | grep -q -v 'exit_code=0'; then
        echo "some runs failed, search for exit_code in ${SUMMARY}" >&2
        return 1
    fi
    echo "all runs finished, summary in ${SUMMARY}"
}

mkdir -p "$RUN_LOG_DIR" "$MODEL_DIR" "$(dirname "$SUMMARY")"

# `:` is the command that does nothing, so this line only applies the redirection.
# That empties the summary. We want it to describe this launch, not every launch ever.
: >"$SUMMARY"

# We run one training at a time. Adding `&` after run_one would push each run to the
# background, and a `wait` at the end would collect them.
# We keep it sequential because it stays easy to read and to debug. Parallel runs also
# share the same cores, so what you gain depends on how much CPU one run already takes
# (sklearn's n_jobs decides that).
for n_estimators in "${N_ESTIMATORS[@]}"; do
    for max_depth in "${MAX_DEPTHS[@]}"; do
        run_one "$n_estimators" "$max_depth"
    done
done

report_failures
