#!/usr/bin/env python3
"""
Evaluate an MCP-served LLM on BoolQ (SuperGLUE).

- Task: Given a passage and a yes/no question, model outputs "yes" or "no".
- Metrics: BLEU, ROUGE-L, Pass@1 (exact, normalized), and latency (ms).
- Saves per-example records to JSON (same shape as Alpaca’s style).

Usage:
  python3 evaluate_boolq.py --url http://localhost:8000/mcp \
    --out results_bare_.../boolq_eval.json --split validation[:500]

Notes:
- Dataset: "super_glue", config "boolq" (fields: question, passage, label where 1=True/Yes, 0=False/No)
"""

import os
import re
import time
import json
import argparse
import requests
from datasets import load_dataset
from tqdm import tqdm
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction


YES_TOKENS = {"yes", "true", "y", "1"}
NO_TOKENS  = {"no", "false", "n", "0"}


def normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_yesno(s: str) -> str:
    """
    Map a free-form string to 'yes' or 'no' when obvious; otherwise return the cleaned string.
    We extract the first a-z token and map common synonyms.
    """
    s_norm = normalize_text(s)
    # Grab the first alphanumeric token
    m = re.search(r"[a-z0-9]+", s_norm)
    tok = m.group(0) if m else s_norm
    if tok in YES_TOKENS:
        return "yes"
    if tok in NO_TOKENS:
        return "no"
    # Heuristic: if it starts with "it is true/false", etc.
    if s_norm.startswith("yes") or s_norm.startswith("true"):
        return "yes"
    if s_norm.startswith("no") or s_norm.startswith("false"):
        return "no"
    return s_norm


def bleu_rouge(hyp: str, ref: str):
    """Compute BLEU and ROUGE-L between two short strings."""
    hyp_n = normalize_text(hyp)
    ref_n = normalize_text(ref)
    bleu = sentence_bleu([ref_n.split()], hyp_n.split(),
                         smoothing_function=SmoothingFunction().method1)
    rouge = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    rougeL = rouge.score(ref_n, hyp_n)['rougeL'].fmeasure
    return round(bleu, 4), round(rougeL, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="MCP server URL, e.g., http://localhost:8000/mcp")
    ap.add_argument("--out", required=True, help="Output JSON path, e.g., results/.../boolq_eval.json")
    ap.add_argument("--split", default="validation[:500]",
                    help="HF split (e.g., train, validation, validation[:500])")
    ap.add_argument("--limit", type=int, default=0, help="Optional cap on items (0 = all)")
    ap.add_argument("--max_tokens", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top_p", type=float, default=0.9)
    args = ap.parse_args()

    ds = load_dataset("super_glue", "boolq", split=args.split)
    rows = list(ds)
    if args.limit and args.limit > 0:
        rows = rows[:args.limit]

    results = []
    for r in tqdm(rows, desc="Evaluating BoolQ"):
        question = r["question"]
        passage  = r["passage"]
        label    = r["label"]  # 1=True, 0=False
        reference = "yes" if int(label) == 1 else "no"

        prompt = (
            "Read the passage and answer the question with a single token: 'yes' or 'no'.\n\n"
            f"Passage:\n{passage}\n\n"
            f"Question: {question}\n"
            "Answer (yes or no):"
        )

        start = time.time()
        try:
            resp = requests.post(args.url, json={
                "prompt": prompt,
                "max_tokens": args.max_tokens,
                "temperature": args.temperature,
                "top_p": args.top_p
            }, timeout=60)
            elapsed_ms = (time.time() - start) * 1000.0
            resp.raise_for_status()
            output_raw = resp.json().get("text", "").strip()
        except Exception as e:
            results.append({
                "question": question,
                "ref": reference,
                "out": "",
                "norm_out": "",
                "latency": None,
                "bleu": 0.0,
                "rouge": 0.0,
                "pass@1": 0,
                "error": str(e)
            })
            continue

        norm_out = normalize_yesno(output_raw)
        bleu, rougeL = bleu_rouge(norm_out, reference)
        pass1 = int(norm_out == reference)

        results.append({
            "question": question,
            "ref": reference,
            "out": output_raw,
            "norm_out": norm_out,
            "latency": round(elapsed_ms, 2),
            "bleu": bleu,
            "rouge": rougeL,
            "pass@1": pass1
        })

    # Save
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved BoolQ eval to {args.out} (n={len(results)})")

if __name__ == "__main__":
    main()
