#!/usr/bin/env bash
# End-to-end orchestration script for the bare-metal MCP benchmark.
# Usage examples:
#   ./run_baremetal.sh 8 32 64 128     # full run
#   ./run_baremetal.sh                 # aggregation-only (if results already exist)

set -euo pipefail

######################## Parameters ########################
SERVER_PORT=8000
VENV_DIR=benchmark_venv
TEST_DURATION=300     # seconds measured per Locust run
WARMUP_DURATION=60    # seconds ignored at start of each run
LOG_DIR="$(pwd)/results_$(date +%Y%m%d_%H%M%S)"
export LOG_DIR                            # <-- now visible to Python
mkdir -p "$LOG_DIR"
################################################################

function banner() { echo -e "\n========= $* ========="; }

################################## (1) venv ##################################
banner "(1) Creating Python virtual environment"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip >/dev/null
pip install fastapi uvicorn locust psutil >/dev/null

################################ (2) server ##################################
banner "(2) Launching MCP server on bare metal"
python mcp_server.py &
SERVER_PID=$!
trap 'echo "Stopping server"; kill $SERVER_PID' EXIT
sleep 3  # allow server to boot fully

################################ (3) load ###################################
if (( $# )); then
  banner "(3) Running workload(s)"
  for users in "$@"; do
    RUN_LOG="$LOG_DIR/locust_${users}users.txt"
    banner "Load = ${users} users (warm-up ${WARMUP_DURATION}s, test ${TEST_DURATION}s)"
    locust -f locustfile.py \
           --headless -u "$users" -r "$users" \
           --host "http://localhost:$SERVER_PORT" \
           --run-time "$((WARMUP_DURATION+TEST_DURATION))s" \
           --csv "$LOG_DIR/metrics_${users}" \
           --only-summary >"$RUN_LOG" 2>&1
    echo -e "\tFinished run – see $RUN_LOG, metrics CSVs"
    sleep 5
  done
else
  banner "(3) No concurrency levels supplied – skipping load generation"
fi

################################ (4) summary #################################
banner "(4) Collecting resource-usage summary"
python - <<'PY'
import os, csv, glob, json, re, sys
LOG_DIR = os.getenv('LOG_DIR')
if not LOG_DIR:
    sys.exit('LOG_DIR not set')

summary = []
for csv_path in glob.glob(os.path.join(LOG_DIR, 'metrics_*_stats.csv')):
    fname = os.path.basename(csv_path)            # e.g. metrics_8_stats.csv
    try:
        users = int(fname.split('_')[1])          # -> 8
    except (IndexError, ValueError):
        continue

    with open(csv_path) as f:
        row = next(csv.DictReader(f))
        # Locate the Requests-per-second column (Locust header differs by version)
        rps_key = next((k for k in row if re.search(r'request.*\/s', k, re.I)), None)
        if rps_key is None:
            raise KeyError('Requests-per-second column not found in CSV')

        summary.append({
            'users': users,
            'p50': float(row.get('50%') or row.get('50') or 0),
            'p95': float(row.get('95%') or row.get('95') or 0),
            'p99': float(row.get('99%') or row.get('99') or 0),
            'rps': float(row[rps_key])
        })

out_path = os.path.join(LOG_DIR, 'summary.json')
with open(out_path, 'w') as f:
    json.dump(sorted(summary, key=lambda x: x['users']), f, indent=2)

print('Summary written to', out_path)
PY

banner "All runs complete. Logs reside in $LOG_DIR"
