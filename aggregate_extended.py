#!/usr/bin/env python3
"""
Aggregate Locust + monitor logs into extended_summary.json
Now records:
  p50/p95/p99, mean & peak CPU/RSS, CPU cycles/request (bare),
  deploy time, cold-start, image size (container).
"""
import sys, os, csv, glob, json, re, statistics

mode, log_dir, deploy_s, cold_ms, *rest = sys.argv[1:]
img_size = int(rest[0]) if rest else None

############ Locust CSVs → per-load ############
def parse_float(val):
    try:
        return float(val)
    except:
        return None

perf = {}
for f in glob.glob(os.path.join(log_dir, 'metrics_*_stats.csv')):
    u = int(os.path.basename(f).split('_')[1])
    r = next(csv.DictReader(open(f)))
    rps_key = next((k for k in r if re.search(r'request.*\/s', k, re.I)), None)

    perf[str(u)] = {
        'p50_ms': parse_float(r.get('50%') or r.get('50')),
        'p95_ms': parse_float(r.get('95%') or r.get('95')),
        'p99_ms': parse_float(r.get('99%') or r.get('99')),
        'throughput_rps': parse_float(r[rps_key]) if rps_key and r.get(rps_key) else None
    }

############ Resource monitor ############
cpu_vals, rss_vals = [], []
docker_log = os.path.join(log_dir, 'docker_stats_raw.json')
pidstat_log = os.path.join(log_dir, 'pidstat_raw.txt')

if os.path.isfile(docker_log):
    for ln in open(docker_log):
        ln = ln.strip()
        if not ln.startswith('{'): continue
        j = json.loads(ln)
        try:
            cpu_vals.append(float(j['cpu'].strip('%')))
            mem = j['mem'].split('/')[0].strip()
            m = re.match(r'([\d\.]+)\s*([KMG]i?B)', mem, re.I)
            if m:
                val, unit = float(m[1]), m[2].upper()
                rss_vals.append(val * {'KB':1/1024,'KIB':1/1024,
                                       'MB':1,'MIB':1,
                                       'GB':1024,'GIB':1024}[unit])
        except:
            continue
elif os.path.isfile(pidstat_log):
    for ln in open(pidstat_log):
        ln = ln.strip()
        if not ln or not ln[0].isdigit() or '%CPU' in ln: continue
        parts = ln.split()
        try:
            cpu_vals.append(float(parts[6]))
            rss_vals.append(float(parts[9]) / 1024)
        except (IndexError, ValueError):
            continue

mean_cpu = round(statistics.mean(cpu_vals), 2) if cpu_vals else 0
peak_cpu = round(max(cpu_vals), 2) if cpu_vals else 0
mean_rss = round(statistics.mean(rss_vals), 1) if rss_vals else 0
peak_rss = round(max(rss_vals), 1) if rss_vals else 0

############ CPU cycles / request (bare) ############
cycles_per_req = None
cycles_path = os.path.join(log_dir, 'perf_cycles.txt')
if os.path.isfile(cycles_path):
    total_cycles = None
    for ln in open(cycles_path):
        if ' cycles' in ln:
            try:
                total_cycles = int(ln.split()[0].replace(',', ''))
            except:
                total_cycles = None
            break
    if total_cycles:
        peak_rps = max((p['throughput_rps'] or 0) for p in perf.values())
        if peak_rps > 0:
            cycles_per_req = round(total_cycles / (peak_rps * (float(deploy_s) + 1)), 0)

############ Dump summary ############
summary = dict(
    mode=mode,
    deploy_time_s=float(deploy_s),
    cold_start_ms=int(cold_ms),
    mean_cpu_pct=mean_cpu,
    peak_cpu_pct=peak_cpu,
    mean_rss_mb=mean_rss,
    peak_rss_mb=peak_rss,
    image_size_bytes=img_size,
    cycles_per_req=cycles_per_req,
    per_load=perf,
)

out = os.path.join(log_dir, 'extended_summary.json')
with open(out, 'w') as f:
    json.dump(summary, f, indent=2)
print("Wrote", out)
