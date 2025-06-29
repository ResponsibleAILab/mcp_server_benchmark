"""Merge bare‑metal and container summaries → CSV & overlay plot."""
import json, sys, pandas as pd, matplotlib.pyplot as plt, pathlib

if len(sys.argv) != 3:
    print("Usage: python compare_results.py <baremetal_dir> <container_dir>")
    sys.exit(1)

bare_dir, cont_dir = map(pathlib.Path, sys.argv[1:])
with open(bare_dir / 'summary.json') as fb, open(cont_dir / 'summary.json') as fc:
    df_bare = pd.DataFrame(json.load(fb)).assign(mode='bare')
    df_cont = pd.DataFrame(json.load(fc)).assign(mode='container')

df = pd.concat([df_bare, df_cont])
print(df.pivot(index='users', columns='mode', values=['p95','rps']))

# ---- Plot ----
fig, ax1 = plt.subplots()
for mode, g in df.groupby('mode'):
    ax1.plot(g['users'], g['p95'], marker='o', label=f'P95 {mode}')
ax1.set_xlabel('Concurrent Users')
ax1.set_ylabel('P95 Latency (ms)')
ax2 = ax1.twinx()
for mode, g in df.groupby('mode'):
    ax2.plot(g['users'], g['rps'], marker='x', linestyle='--', label=f'Throughput {mode}')
ax2.set_ylabel('Requests/s')
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')
plt.title('Bare‑Metal vs Container Performance')
plt.tight_layout()
plt.savefig('comparison_plot.png')
print('Saved comparison_plot.png')