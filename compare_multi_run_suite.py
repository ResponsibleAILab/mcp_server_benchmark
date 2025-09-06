#!/usr/bin/env python3
"""
Aggregate N runs of bare-metal and container experiments (datasets + extended),
then compare them with CSV tables and plots.

Inputs (repeatable flags):
  --bare DIR [--bare DIR ...]
  --ctn  DIR [--ctn  DIR ...]
  --out OUTDIR  (default: ./multi_run_report)

Looks for (in each DIR):
  extended_summary.json
  alpaca_eval.json
  squad_eval.json
  boolq_eval.json

Outputs (in OUTDIR):
  datasets_summary.csv                 (long form mean ± 95% CI)
  datasets_summary_wide.csv            (wide form means only)
  metrics_combined_latency.png         (all datasets; bars: Bare vs Container; log y)
  metrics_combined_bleu.png
  metrics_combined_rouge.png
  metrics_combined_pass1.png
  latex_table_latency.tex              (LaTeX tabular)
  latex_table_bleu.tex
  latex_table_rouge.tex
  latex_table_pass1.tex
  combined_perf_users.png              (one figure with twin y-axes: p95 + rps, both envs)
  extended_ops_summary.csv             (means ± CI for ops metrics)
  per_run_index.csv
"""

import argparse, json, os, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({"figure.dpi": 160, "savefig.dpi": 160})

DATASETS = ["Alpaca", "SQuADv2", "BoolQ"]
ENVS = ["Bare-Metal", "Container"]
DS_METRICS = ["bleu", "rouge", "pass1", "latency_ms"]
DS_METRIC_LABEL = {
    "bleu": "BLEU",
    "rouge": "ROUGE-L",
    "pass1": "Pass@1",
    "latency_ms": "Avg Latency (ms)"
}

def ci95(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    m = x.mean()
    if len(x) == 1:
        return (m, m, m)
    se = x.std(ddof=1) / math.sqrt(len(x))
    d = 1.96 * se
    return (m, m - d, m + d)

def safe_mean(vals):
    vals = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.mean(vals)) if vals else np.nan

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def agg_dataset_file(path):
    data = load_json(path)
    if not isinstance(data, list) or len(data) == 0:
        return dict(bleu=np.nan, rouge=np.nan, pass1=np.nan, latency_ms=np.nan, count=0)
    bleu = safe_mean([d.get("bleu") for d in data])
    rouge = safe_mean([d.get("rouge") for d in data])
    p1   = safe_mean([d.get("pass@1") for d in data])
    lat  = safe_mean([d.get("latency") for d in data])
    return dict(bleu=bleu, rouge=rouge, pass1=p1, latency_ms=lat, count=len(data))

def agg_extended_file(path):
    js = load_json(path)
    if not isinstance(js, dict):
        return None
    ops = dict(
        deploy_time_s=js.get("deploy_time_s"),
        cold_start_ms=js.get("cold_start_ms"),
        mean_cpu_pct=js.get("mean_cpu_pct"),
        peak_cpu_pct=js.get("peak_cpu_pct"),
        mean_rss_mb=js.get("mean_rss_mb"),
        peak_rss_mb=js.get("peak_rss_mb"),
        image_size_bytes=js.get("image_size_bytes"),
        cycles_per_req=js.get("cycles_per_req"),
    )
    per_load_rows = []
    pl = js.get("per_load") or {}
    for u, rec in pl.items():
        try:
            users = int(u)
        except Exception:
            continue
        per_load_rows.append(dict(users=users,
                                  p95_ms=rec.get("p95_ms"),
                                  throughput_rps=rec.get("throughput_rps")))
    perf_df = pd.DataFrame(per_load_rows) if per_load_rows else pd.DataFrame(columns=["users","p95_ms","throughput_rps"])
    return ops, perf_df

def collect_runs(dirs, env_label):
    ds_rows = []
    ops_rows = []
    perf_rows = []
    for ridx, rdir in enumerate(dirs, start=1):
        rdir = Path(rdir)
        for ds_name, fname in [("Alpaca","alpaca_eval.json"),
                               ("SQuADv2","squad_eval.json"),
                               ("BoolQ","boolq_eval.json")]:
            vals = agg_dataset_file(rdir / fname)
            ds_rows.append(dict(env=env_label, run=ridx, run_dir=str(rdir),
                                dataset=ds_name, **vals))
        ext = agg_extended_file(rdir / "extended_summary.json")
        if ext:
            ops, perf = ext
            ops_rows.append(dict(env=env_label, run=ridx, run_dir=str(rdir), **ops))
            if not perf.empty:
                perf = perf.copy()
                perf["env"] = env_label
                perf["run"] = ridx
                perf["run_dir"] = str(rdir)
                perf_rows.append(perf)
    ds_df = pd.DataFrame(ds_rows)
    ops_df = pd.DataFrame(ops_rows)
    perf_df = pd.concat(perf_rows, ignore_index=True) if perf_rows else pd.DataFrame(columns=["users","p95_ms","throughput_rps","env","run","run_dir"])
    return ds_df, ops_df, perf_df

def bar_with_ci_all_datasets(ds_summary, metric, out_path, use_log=False):
    """One figure: all datasets on x-axis; two bars (Bare/Container) per dataset, with 95% CI + hatches."""
    fig, ax = plt.subplots(figsize=(9.5, 5))
    order_ds = DATASETS
    x = np.arange(len(order_ds))
    width = 0.5  # your chosen group bar width

    # --- Subtle alternating background bands per dataset group ---
    for i in range(len(order_ds)):
        if i % 2 == 0:  # shade every other dataset group
            ax.axvspan(i - width, i + width, facecolor="lightgray", alpha=0.12, zorder=0)

    # Hatch patterns for each env (distinct + print-friendly)
    hatches = {
        "Bare-Metal": "//",
        "Container":  "xx",
    }

    # --- Bars + error bars ---
    for i, env in enumerate(ENVS):
        chunk = ds_summary[(ds_summary["metric"] == metric) & (ds_summary["env"] == env)]
        chunk = chunk.set_index("dataset").reindex(order_ds)
        means = chunk["mean"].values.astype(float)
        lows  = chunk["ci_low"].values.astype(float)
        highs = chunk["ci_high"].values.astype(float)

        # bars
        ax.bar(
            x + (i - 0.5) * width, means, width,
            label=env,
            hatch=hatches.get(env, ""),
            edgecolor="black",
            linewidth=0.8,
            zorder=2,
        )

        # 95% CI error bars
        err_lo = np.clip(means - lows, 0, None)
        err_hi = np.clip(highs - means, 0, None)
        ax.errorbar(
            x + (i - 0.5) * width, means,
            yerr=[err_lo, err_hi],
            fmt='none', capsize=4, ecolor='black',
            elinewidth=1.0, capthick=1.0, alpha=0.9, zorder=3
        )

    # Axes cosmetics
    ax.set_xticks(x)
    ax.set_xticklabels(order_ds, fontsize=14)
    ax.set_ylabel(DS_METRIC_LABEL[metric], fontsize=16)
    ax.tick_params(axis="y", labelsize=14)
    ax.tick_params(axis="x", labelsize=14)
    if use_log:
        ax.set_yscale("log")
    ax.legend(fontsize=16)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

def write_latex_table(ds_summary, metric, out_path):
    """Save a LaTeX tabular: rows=datasets, cols=Bare, Container (means), plus 95% CI."""
    sub = ds_summary[ds_summary["metric"]==metric].copy()
    # Build a wide form with mean ± CI text
    def fmt_row(group):
        m = group.set_index("env")
        def fmt(env):
            if env not in m.index or pd.isna(m.loc[env,"mean"]):
                return "--"
            mean = m.loc[env,"mean"]
            lo   = m.loc[env,"ci_low"]
            hi   = m.loc[env,"ci_high"]
            if metric == "latency_ms":
                return f"{mean:.1f} ({lo:.1f}-{hi:.1f})"
            else:
                return f"{mean:.4f} ({lo:.4f}-{hi:.4f})"
        return pd.Series({"Bare-Metal": fmt("Bare-Metal"), "Container": fmt("Container")})

    rows = []
    for ds, g in sub.groupby("dataset"):
        rows.append(pd.concat([pd.Series({"Dataset": ds}), fmt_row(g)]))
    table = pd.DataFrame(rows)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("% Auto-generated table\n")
        f.write("\\begin{table}[t]\n\\centering\n")
        f.write(f"\\caption{{{DS_METRIC_LABEL[metric]} (mean $\\pm$ 95\\% CI) across datasets}}\n")
        f.write("\\begin{tabular}{lcc}\n\\toprule\n")
        f.write("Dataset & Bare-Metal & Container \\\\\n\\midrule\n")
        for _, r in table.iterrows():
            f.write(f"{r['Dataset']} & {r['Bare-Metal']} & {r['Container']} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bare', nargs='+', required=True, help='bare-metal run directories')
    ap.add_argument('--ctn',  nargs='+', required=True, help='container run directories')
    ap.add_argument('--out', default='multi_run_report', help='output directory')
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # collect
    b_ds, b_ops, b_perf = collect_runs(args.bare, 'Bare-Metal')
    c_ds, c_ops, c_perf = collect_runs(args.ctn,  'Container')

    # bookkeeping
    per_run_index = pd.concat([
        b_ds[['env','run','run_dir']].drop_duplicates(),
        c_ds[['env','run','run_dir']].drop_duplicates(),
    ], ignore_index=True)
    per_run_index.to_csv(outdir / 'per_run_index.csv', index=False)

    # ----- DATASETS: aggregate across runs -----
    ds_all = pd.concat([b_ds, c_ds], ignore_index=True)

    # mean ± CI per dataset & env
    rows = []
    for ds in DATASETS:
        for env in ENVS:
            sub = ds_all[(ds_all['dataset']==ds) & (ds_all['env']==env)]
            for metric in DS_METRICS:
                m, lo, hi = ci95(pd.to_numeric(sub[metric], errors='coerce').values)
                rows.append(dict(dataset=ds, env=env, metric=metric, mean=m, ci_low=lo, ci_high=hi, n=len(sub)))
    ds_summary = pd.DataFrame(rows)
    ds_summary.to_csv(outdir / 'datasets_summary.csv', index=False)

    # wide means only (handy for quick tables)
    wide_rows = []
    for ds in DATASETS:
        rec = {"Dataset": ds}
        for env in ENVS:
            sub = ds_summary[(ds_summary["dataset"]==ds) & (ds_summary["env"]==env)]
            for metric in DS_METRICS:
                val = sub[sub["metric"]==metric]["mean"]
                rec[f"{env}_{metric}"] = float(val.values[0]) if len(val) else np.nan
        wide_rows.append(rec)
    pd.DataFrame(wide_rows).to_csv(outdir / 'datasets_summary_wide.csv', index=False)

    # ---- Combined metric plots (all datasets on one chart)
    bar_with_ci_all_datasets(ds_summary, "latency_ms", outdir / "metrics_combined_latency.pdf", use_log=True)
    bar_with_ci_all_datasets(ds_summary, "bleu",       outdir / "metrics_combined_bleu.pdf")
    bar_with_ci_all_datasets(ds_summary, "rouge",      outdir / "metrics_combined_rouge.pdf")
    bar_with_ci_all_datasets(ds_summary, "pass1",      outdir / "metrics_combined_pass1.pdf")

    # ---- LaTeX tables per metric
    write_latex_table(ds_summary, "latency_ms", outdir / "latex_table_latency.tex")
    write_latex_table(ds_summary, "bleu",       outdir / "latex_table_bleu.tex")
    write_latex_table(ds_summary, "rouge",      outdir / "latex_table_rouge.tex")
    write_latex_table(ds_summary, "pass1",      outdir / "latex_table_pass1.tex")

    # ----- EXTENDED: per-load curves combined on ONE figure (p95 + rps; both envs)
    perf_all = pd.concat([b_perf, c_perf], ignore_index=True)
    if not perf_all.empty:
        # Aggregate means and 95% CI by env & users
        lines = {}
        for env in ENVS:
            sub = perf_all[perf_all["env"]==env]
            if sub.empty:
                continue
            g = sub.groupby("users")
            users_sorted = sorted(g.groups.keys())
            def agg_col(col):
                means, lows, highs = [], [], []
                for u in users_sorted:
                    vals = pd.to_numeric(g.get_group(u)[col], errors='coerce').values
                    m, lo, hi = ci95(vals)
                    means.append(m); lows.append(lo); highs.append(hi)
                return users_sorted, np.array(means), np.array(lows), np.array(highs)
            ul, p95_m, p95_lo, p95_hi = agg_col("p95_ms")
            _,  rps_m, rps_lo, rps_hi = agg_col("throughput_rps")
            lines[env] = dict(users=ul, p95=(p95_m,p95_lo,p95_hi), rps=(rps_m,rps_lo,rps_hi))

        fig, ax1 = plt.subplots(figsize=(9.5,5))
        ax2 = ax1.twinx()
        # Plot p95 on ax1, rps on ax2
        colors = {"Bare-Metal":"tab:blue", "Container":"tab:orange"}
        for env in ENVS:
            if env not in lines: continue
            ul = lines[env]["users"]
            p95_m, p95_lo, p95_hi = lines[env]["p95"]
            rps_m, rps_lo, rps_hi = lines[env]["rps"]
            ax1.plot(ul, p95_m, marker='o', color=colors[env], label=f"{env} P95 (ms)")
            ax1.fill_between(ul, p95_lo, p95_hi, color=colors[env], alpha=0.15)
            ax2.plot(ul, rps_m, marker='s', linestyle='--', color=colors[env], label=f"{env} RPS")
            ax2.fill_between(ul, rps_lo, rps_hi, color=colors[env], alpha=0.10)

        ax1.set_xlabel("Concurrent users")
        ax1.set_ylabel("P95 latency (ms)")
        ax2.set_ylabel("Throughput (req/s)")
        fig.suptitle("Per-load performance (mean ± 95% CI): P95 latency & Throughput")
        # Build a combined legend
        lines_, labels_ = [], []
        for ax in (ax1, ax2):
            lns, lbs = ax.get_legend_handles_labels()
            lines_ += lns; labels_ += lbs
        fig.legend(lines_, labels_, loc="upper center", ncol=2)
        fig.tight_layout(rect=[0,0,1,0.90])
        fig.savefig(outdir / "combined_perf_users.pdf", bbox_inches="tight", pad_inches=0)
        plt.close(fig)

    # Also export ops summary for completeness
    ops_all = pd.concat([b_ops.assign(env='Bare-Metal'), c_ops.assign(env='Container')], ignore_index=True)
    ops_all.to_csv(outdir / "extended_ops_summary.csv", index=False)

    print(f"\nWrote outputs to: {outdir.resolve()}")
    print("  - datasets_summary.csv / datasets_summary_wide.csv")
    print("  - metrics_combined_latency.pdf / _bleu.pdf / _rouge.pdf / _pass1.pdf")
    print("  - latex_table_latency.tex / _bleu.tex / _rouge.tex / _pass1.tex")
    print("  - combined_perf_users.pdf")
    print("  - extended_ops_summary.csv")
    print("  - per_run_index.csv")

if __name__ == "__main__":
    main()
