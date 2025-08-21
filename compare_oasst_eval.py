#!/usr/bin/env python3
"""
Compare OASST evaluation results between bare-metal and container runs.
Each file contains a list of evaluation entries with BLEU, ROUGE, Pass@1, and latency.
Also generates a comparison bar chart for visual inspection.
"""

import sys
import json
import pandas as pd
import matplotlib.pyplot as plt

if len(sys.argv) != 3:
    print("Usage: python compare_oasst_eval.py <baremetal_eval.json> <container_eval.json>")
    sys.exit(1)

def load_and_aggregate(path):
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        print(f" Error: '{path}' is empty or not a list of records.")
        sys.exit(1)

    required_keys = {"bleu", "rouge", "pass@1", "latency"}
    if not all(required_keys <= data[0].keys()):
        print(f" Error: Missing required keys in '{path}'")
        print(f"Found keys: {list(data[0].keys())}")
        sys.exit(1)

    return {
        "bleu": round(sum(x["bleu"] for x in data) / len(data), 4),
        "rouge": round(sum(x["rouge"] for x in data) / len(data), 4),
        "pass@1": round(sum(x["pass@1"] for x in data) / len(data), 4),
        "latency_ms": round(sum(x["latency"] for x in data) / len(data), 2)
    }


bare = load_and_aggregate(sys.argv[1])
cont = load_and_aggregate(sys.argv[2])

df = pd.DataFrame([
    {"Metric": "BLEU", "Bare-Metal": bare["bleu"], "Container": cont["bleu"]},
    {"Metric": "ROUGE", "Bare-Metal": bare["rouge"], "Container": cont["rouge"]},
    {"Metric": "Pass@1", "Bare-Metal": bare["pass@1"], "Container": cont["pass@1"]},
    {"Metric": "Avg Latency (ms)", "Bare-Metal": bare["latency_ms"], "Container": cont["latency_ms"]},
]).set_index("Metric")

print(df)
df.to_csv("oasst_eval_comparison.csv")
print("\nSaved: oasst_eval_comparison.csv")

# ---- Visualization ----
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle("OASST Evaluation: Bare-Metal vs Container", fontsize=16)

metrics = df.index.tolist()
colors = ["royalblue", "forestgreen"]
positions = df.columns.tolist()

# Subplot (0,0): BLEU
axs[0, 0].bar(positions, df.loc["BLEU"], color=colors)
axs[0, 0].set_title("BLEU Score")
axs[0, 0].set_ylim(0, 1)

# Subplot (0,1): ROUGE
axs[0, 1].bar(positions, df.loc["ROUGE"], color=colors)
axs[0, 1].set_title("ROUGE Score")
axs[0, 1].set_ylim(0, 1)

# Subplot (1,0): Pass@1
axs[1, 0].bar(positions, df.loc["Pass@1"], color=colors)
axs[1, 0].set_title("Pass@1 Accuracy")
axs[1, 0].set_ylim(0, 1)

# Subplot (1,1): Latency
axs[1, 1].bar(positions, df.loc["Avg Latency (ms)"], color=colors)
axs[1, 1].set_title("Average Latency (ms)")
axs[1, 1].set_ylim(0, max(df.loc["Avg Latency (ms)"]) * 1.2)

# Annotate each bar
for ax in axs.flat:
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.3f}',
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom')

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig("oasst_eval_comparison_plot.png")
print("Saved: oasst_eval_comparison_plot.png")
plt.show()
