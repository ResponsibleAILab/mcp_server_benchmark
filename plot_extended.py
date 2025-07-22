import json, sys, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path

# ——— Load extended_summary.json files ———
bare_path, ctn_path = sys.argv[1:3]
with open(bare_path) as f: bare = json.load(f)
with open(ctn_path)  as f: ctn  = json.load(f)

# ——— Per-load (users) section ———
users = sorted(int(k) for k in bare["per_load"])
lat_b = [bare['per_load'][str(u)]['p95_ms'] for u in users]
lat_c = [ctn ['per_load'][str(u)]['p95_ms'] for u in users]
rps_b = [bare['per_load'][str(u)]['throughput_rps'] for u in users]
rps_c = [ctn ['per_load'][str(u)]['throughput_rps'] for u in users]

# ——— Plot 1: Latency + Throughput ———
fig, ax1 = plt.subplots()
ax1.plot(users, lat_b, 'o-', label='Latency (bare)', alpha=0.8)
ax1.plot(users, lat_c, 's--', label='Latency (ctn)', alpha=0.8)
ax1.set_ylabel('P95 Latency (ms)')
ax1.set_xlabel('Concurrent Users')
ax2 = ax1.twinx()
ax2.plot(users, rps_b, 'o-', label='RPS (bare)', alpha=0.5, color='green')
ax2.plot(users, rps_c, 's--', label='RPS (ctn)', alpha=0.5, color='orange')
ax2.set_ylabel('Throughput (requests/sec)')
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
plt.legend(lines + lines2, labels + labels2, loc='upper left')
plt.title('Performance vs Load')
fig.tight_layout()
plt.savefig('perf_vs_users.pdf')
plt.close()

# ——— Plot 2: Deployment metrics ———
metrics = ['deploy_time_s', 'cold_start_ms', 'mean_cpu_pct', 'mean_rss_mb']
bars = [(bare.get(m, 0), ctn.get(m, 0)) for m in metrics]
bar_df = pd.DataFrame(bars, index=metrics, columns=["Bare", "Container"])
bar_df.plot.bar(rot=45)
plt.title('Deployment + Resource Usage')
plt.tight_layout()
plt.savefig('resource_vs_users.pdf')
plt.close()

# ——— Table 1: Per-load ———
with open("perf_table.tex", "w") as f:
    f.write("\\begin{table}[t]\n\\caption{Per-load latency and throughput}\n\\centering\n")
    f.write("\\begin{tabular}{r|cc|cc}\n")
    f.write("Users & Lat(B) & Lat(C) & RPS(B) & RPS(C) \\\\\n\\hline\n")
    for i, u in enumerate(users):
        f.write(f"{u} & {lat_b[i]:.1f} & {lat_c[i]:.1f} & {rps_b[i]:.1f} & {rps_c[i]:.1f} \\\\\n")
    f.write("\\end{tabular}\n\\end{table}\n")

# ——— Table 2: Run-level ———
keys = sorted(set(k for k in bare if k != 'per_load'))
with open("ops_table.tex", "w") as f:
    f.write("\\begin{table}[t]\n\\caption{Deployment and system metrics}\n\\centering\n")
    f.write("\\begin{tabular}{lcc}\n")
    f.write("Metric & Bare & Container \\\\\n\\hline\n")
    for k in keys:
        vb = bare.get(k, "--")
        vc = ctn.get(k, "--")
        f.write(f"{k.replace('_','\\_')} & {vb} & {vc} \\\\\n")
    f.write("\\end{tabular}\n\\end{table}\n")

print("Created perf_vs_users.pdf, resource_vs_users.pdf, perf_table.tex, ops_table.tex")
