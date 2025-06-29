#!/usr/bin/env bash
# monitor_pidstat.sh PID PIDSTAT_OUT PERF_OUT
# Records 1 Hz CPU/RSS via pidstat and total CPU cycles via perf.
set -euo pipefail
PID=$1
PIDSTAT_OUT=$2
PERF_OUT=$3

# 1 Hz CPU/RSS
pidstat -rud -p "$PID" 1 >"$PIDSTAT_OUT" &
MON1=$!

# CPU cycles (one long sample)
perf stat -e cycles -p "$PID" -- sleep 999999 2>"$PERF_OUT" &
MON2=$!

echo "$MON1 $MON2"           # caller can kill both PIDs later
