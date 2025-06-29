#!/usr/bin/env bash
# Extended bare-metal benchmark  –  collects full metric set.
set -euo pipefail
SERVER_PORT=8000
VENV_DIR=benchmark_venv
TEST_DURATION=300
WARMUP_DURATION=60
LOG_DIR="$(pwd)/results_bare_$(date +%Y%m%d_%H%M%S)"
export LOG_DIR; mkdir -p "$LOG_DIR"

banner(){ echo -e "\n========= $* ========="; }

### (0) Deploy timer
SECONDS=0
python3 -m venv "$VENV_DIR" && source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip fastapi uvicorn locust psutil >/dev/null
DEPLOY_TIME=$SECONDS

### (1) Cold-start timer
START_MS=$(date +%s%3N)
python mcp_server.py & SRV_PID=$!
trap 'kill "$SRV_PID" 2>/dev/null || true' EXIT
until curl -s -o /dev/null -w '%{http_code}' http://localhost:$SERVER_PORT/mcp \
         -X POST -d '{"prompt":"ping"}' -H "Content-Type: application/json" \
         | grep -q 200; do sleep 0.1; done
COLD_MS=$(( $(date +%s%3N) - START_MS ))

### (2) Start monitors
read PIDSTAT_ID PERF_ID < <(./monitor_pidstat.sh \
        "$SRV_PID" "$LOG_DIR/pidstat_raw.txt" "$LOG_DIR/perf_cycles.txt")

### (3) Load loops
for users in "$@"; do
  echo "Load = $users users"
  locust -f locustfile.py --headless -u "$users" -r "$users" \
         --host http://localhost:$SERVER_PORT \
         --run-time "$((WARMUP_DURATION+TEST_DURATION))s" \
         --csv "$LOG_DIR/metrics_${users}" --only-summary \
         >"$LOG_DIR/locust_${users}users.txt" 2>&1
  sleep 5
done

### (5) Aggregate
python aggregate_extended.py bare "$LOG_DIR" "$DEPLOY_TIME" "$COLD_MS"
echo "✅  Bare-metal extended_summary.json at $LOG_DIR"

### (4) Cleanup
kill $PIDSTAT_ID $PERF_ID 2>/dev/null || true
wait $PIDSTAT_ID $PERF_ID 2>/dev/null || true
kill "$SRV_PID" 2>/dev/null || true

