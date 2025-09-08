# **Evaluating Containerization Overhead in MCP Servers for Scalable LLM Inference: A Comparative Benchmark Study**

# **Abstract**

In recent years, the deployment of large language models (LLMs) through service-oriented architectures has gained traction in both research and production environments. However, few studies systematically evaluate the trade-offs between containerized and bare-metal deployments of model hosts in real-world scenarios—particularly for latency-sensitive applications involving LLMs. This paper investigates the performance implications of containerizing an MCP (Model Context Protocol) server responsible for hosting a lightweight LLM evaluated using multiple datasets. _By comparing container-based and bare-metal deployments_, we analyze key performance metrics across multiple concurrent load levels. The goal is to determine whether containerized execution—often promoted for its scalability, reproducibility, and ease of deployment—introduces measurable overhead or compromises real-time model inference quality. Through rigorous benchmarking and extended resource monitoring, we provide empirical evidence suggesting that containerized MCP-served LLMs maintain comparable inference quality to bare-metal implementations, with negligible latency trade-offs under low-to-moderate concurrent user loads. Our findings reinforce the viability of containerization for scalable LLM serving in production systems and DevOps pipelines, where reliability, modularity, and automation are critical.
The code is available at: https://github.com/ResponsibleAILab/mcp_server_benchmark.

## Containerized MCP Server Framework

The following diagram illustrates the architecture of the containerized MCP server framework.

![Containerized MCP Server Framework](Images/MCP_Container_Diagram-update.drawio.svg)

## Key Metrics

| Metric          | Meaning                                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| **BLEU**        | Measures **n-gram overlap** between the generated output and the reference. Higher = better accuracy.       |
| **ROUGE**       | Measures **recall**-based similarity (focuses on how much of the reference is captured).                    |
| **Pass\@1**     | Fraction of examples where the generated output **matches exactly** (often used in coding tasks, stricter). |
| **Avg Latency** | Average time (in milliseconds) the server took to respond to each prompt. Lower = faster.                   |

## Key Results
**Accuracy (BLEU, ROUGE-L, Pass@1):**  
Containerized deployments achieved near-parity with bare-metal across all datasets, with differences within one standard deviation and overlapping 95% confidence intervals.

**Latency:**  
Bare-metal runs were consistently faster, especially on longer outputs (e.g., Alpaca), but container overhead was modest and remained within practical tolerances.

**Overall Finding:**  
Containerization introduces negligible accuracy loss while providing the benefits of portability, reproducibility, and ease of deployment, making it a viable choice for scalable LLM inference.

### Evaluation Metrics for Bare-Metal vs. Container (Mean ± SD)

#### BLEU

| Dataset |      Bare-Metal |       Container |
| :------ | --------------: | --------------: |
| Alpaca  | 0.0653 ± 0.0022 | 0.0630 ± 0.0014 |
| BoolQ   | 0.1221 ± 0.0012 | 0.1204 ± 0.0010 |
| SQuADv2 | 0.1507 ± 0.0036 | 0.1482 ± 0.0025 |

#### ROUGE-L

| Dataset |      Bare-Metal |       Container |
| :------ | --------------: | --------------: |
| Alpaca  | 0.2513 ± 0.0024 | 0.2527 ± 0.0014 |
| BoolQ   | 0.6865 ± 0.0071 | 0.6772 ± 0.0057 |
| SQuADv2 | 0.6794 ± 0.0063 | 0.6853 ± 0.0121 |

#### Pass\@1

| Dataset |      Bare-Metal |       Container |
| :------ | --------------: | --------------: |
| Alpaca  | 0.0190 ± 0.0021 | 0.0164 ± 0.0017 |
| BoolQ   | 0.6865 ± 0.0071 | 0.6772 ± 0.0057 |
| SQuADv2 | 0.3846 ± 0.0110 | 0.3802 ± 0.0124 |

#### Latency *(ms)*

| Dataset |    Bare-Metal |     Container |
| :------ | ------------: | ------------: |
| Alpaca  | 2112.2 ± 18.4 | 2153.1 ± 22.4 |
| BoolQ   |    46.7 ± 3.1 |    47.4 ± 2.5 |
| SQuADv2 |   171.8 ± 8.0 |   186.0 ± 8.2 |

*Notes:* All values are reported as **Mean ± Standard Deviation**.



## Installation
1. Install Python v3.10+
2. Set up a Python virtual environment

### On Windows (PowerShell)
```bash
python3 -m venv benchmark_venv
.\benchmark_venv\Scripts\Activate
pip3 install -r requirements.txt
.\benchmark_venv\Scripts\Deactivate
```

### On Linux / macOS
```bash
python3 -m venv benchmark_venv
source benchmark_venv/bin/activate
pip3 install -r requirements.txt
deactivate
```

### All Operating System options need Docker
- Windows use Docker Desktop
- Linux install docker

## To Run
You DO NOT want to be in a venv when you execute the below bash script. It will call others to run bare-metal and container shell scripts.

```bash
./run_all.sh
```
This will run 10 iterations of both bare-metal and container saving the results from each one

## Compare Results
Replace results_bare_* and results_ctn_* with yours that are generated when you run the following command.

```bash
python3 compare_multi_run_suite.py \
  --bare results_bare_20250720_101500 results_bare_20250720_111530 results_bare_20250720_121601 results_bare_20250720_131633 results_bare_20250720_141704 \
  --ctn  results_ctn_20250720_102040  results_ctn_20250720_112115  results_ctn_20250720_122146  results_ctn_20250720_132218  results_ctn_20250720_142249 \
  --out  multi_run_report
```
This is an example of getting all bare-metal and container reports compared and saved for evaluating results.

## **Citation**
If you find this work useful, please cite it as follows:

```bibtex
@inproceedings{SteeleFeng2025MCP,
  author    = {Michael Steele and Yunhe Feng},
  title     = {Evaluating Containerization Overhead in {MCP} Servers for Scalable {LLM} Inference: A Comparative Benchmark Study},
  booktitle = {Proceedings of the Integrated Approaches to Testing Data-Centric {AI} Systems: Methods, Metrics, and Benchmarks Workshop at {IEEE} Artificial Intelligence x Software Engineering ({AIxSE})},
  year      = {2025},
  publisher = {IEEE},
  note      = {Workshop paper}
}
```

## **Acknowledgements**

This work was supported in part by the National Science Foundation CCF-2447834.




