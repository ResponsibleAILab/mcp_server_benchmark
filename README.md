# MCP Performance Benchmark Suite

This repository provides tools for benchmarking the performance of a minimal MCP (Model Context Protocol) server under both **bare-metal** and **containerized** conditions.

You can choose between:

- **Classic Workflow (OLD)**: Measures latency and throughput only  
- **Extended Workflow (NEW)**: Captures additional system-level metrics including cold-start, CPU/RSS usage, deploy time, and container image size

---

## Quick Start

### Workflow Options

| Workflow       | Description                                    |
|----------------|------------------------------------------------|
| Classic        | Fast latency and throughput comparison         |
| Extended       | Full system metrics, figures, and tables       |

---

## Classic Workflow (Latency & Throughput Only)

### A. Containerized Benchmark
```bash
chmod +x run_container.sh
./run_container.sh 8 32 64 128   # Run with different concurrency levels
```
### B. Bare-Metal Benchmark
```bash
chmod +x run_baremetal.sh
./run_baremetal.sh 8 32 64 128
```
### C. Compare Results
```bash
python compare_results.py \
  results_20250701_1530            # bare-metal results dir
  results_container_20250701_1600  # container results dir
```

## Extended Workflow (Full Systems Metrics)
### A. Bare-Metal Extended Benchmark
```bash
chmod +x run_baremetal_ext.sh monitor_pidstat.sh
./run_baremetal_ext.sh 8 32 64 128
```

### B. Container Extended Benchmark
```bash
chmod +x run_container_ext.sh
./run_container_ext.sh 8 32 64 128
```

### C. Generate Plots and Tables
```bash
python plot_extended.py \
  results_bare_20250701_1410/extended_summary.json \
  results_ctn_20250701_1450/extended_summary.json
```

## Using Alpaca Dataset w/ LLaMA 3.2-1B-Instruct

The alpaca dataset is a collection of ~52000 synthetic prompt-response pairs originally curated by Stanford CRFM.

```bash
python3 compare_alpaca_eval.py \
  results_bare_*/alpaca_eval.json \
  results_ctn_*/alpaca_eval.json
```

| Metric          | Meaning                                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| **BLEU**        | Measures **n-gram overlap** between the generated output and the reference. Higher = better accuracy.       |
| **ROUGE**       | Measures **recall**-based similarity (focuses on how much of the reference is captured).                    |
| **Pass\@1**     | Fraction of examples where the generated output **matches exactly** (often used in coding tasks, stricter). |
| **Avg Latency** | Average time (in milliseconds) the server took to respond to each prompt. Lower = faster.                   |
