#!/usr/bin/env bash
# Extended container benchmark – full metric set (no perf cycles).
# set -euo pipefail

IMAGE=mcp_server:bench
VENV_DIR=benchmark_venv
SERVER_PORT=8000
TEST_DURATION=300
WARMUP_DURATION=60
LOG_DIR="$(pwd)/results_ctn_$(date +%Y%m%d_%H%M%S)"
export LOG_DIR; mkdir -p "$LOG_DIR"

banner(){ echo -e "\n========= $* ========="; }

### (0) Build timer + image size
SECONDS=0
python3 -m venv "$VENV_DIR" && source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip fastapi uvicorn locust psutil >/dev/null
docker build -t "$IMAGE" -f Dockerfile .
BUILD_TIME=$SECONDS
IMG_SIZE=$(docker image inspect "$IMAGE" --format='{{.Size}}')

### (1) Cold-start timer and run container with GPU
START_MS=$(date +%s%3N)
docker run --gpus all --rm -d \
  -p $SERVER_PORT:8000 \
  --name mcp_bench \
  "$IMAGE"

# Wait for MCP endpoint to be available
until curl -s -o /dev/null -w '%{http_code}' http://localhost:$SERVER_PORT/mcp \
         -X POST -d '{"prompt":"ping"}' -H "Content-Type: application/json" \
         | grep -q 200; do sleep 0.1; done
COLD_MS=$(( $(date +%s%3N) - START_MS ))

### (2) docker stats monitor (JSON 1 Hz)
docker stats --no-stream=false --format \
'{"cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}"}' mcp_bench \
> "$LOG_DIR/docker_stats_raw.json" &
MON_ID=$!

### (3) Load testing with Locust
for users in "$@"; do
  echo "Load = $users users"
  locust -f locustfile.py --headless -u "$users" -r "$users" \
         --host "http://localhost:$SERVER_PORT" \
         --run-time "$((WARMUP_DURATION+TEST_DURATION))s" \
         --csv "$LOG_DIR/metrics_${users}" --only-summary \
         >"$LOG_DIR/locust_${users}users.txt" 2>&1
  sleep 5
done

### (4) Evaluate Alpaca BEFORE container shuts down
echo "Evaluating Alpaca dataset..."
python3 evaluate/evaluate_alpaca.py \
    --url "http://localhost:$SERVER_PORT/mcp" \
    --out "$LOG_DIR/alpaca_eval.json"

### (5) Evaluate SQuAD v2
echo "Evaluating SQuAD v2 (container)..."
python3 evaluate/evaluate_squad.py \
  --url "http://localhost:$SERVER_PORT/mcp" \
  --out "$LOG_DIR/squad_eval.json" \
  --split "validation[:200]"

### (6) Evaluate BoolQ
echo "Evaluating BoolQ (container)..."
python3 evaluate/evaluate_boolq.py \
  --url "http://localhost:$SERVER_PORT/mcp" \
  --out "$LOG_DIR/boolq_eval.json" \
  --split "validation[:500]"

### (7) Cleanup
kill $MON_ID 2>/dev/null || true
docker stop mcp_bench || true

### (8) Aggregate results
python3 aggregate_extended.py container "$LOG_DIR" "$BUILD_TIME" "$COLD_MS" "$IMG_SIZE"
echo "Container extended_summary.json at $LOG_DIR"