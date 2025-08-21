#!/usr/bin/env python3
"""
Evaluate an MCP-served LLM on SQuAD v2 (Q&A).
- Filters to answerable questions (is_impossible == False).
- Uses multiple reference answers (takes the best BLEU/ROUGE across refs).
- Logs latency, BLEU, ROUGE-L, and Pass@1 (strict normalized match).
- Saves per-example records to JSON.

Usage:
  python3 evaluate_squad.py --url http://localhost:8000/mcp --out results/.../squad_eval.json
  # Optional:
  #   --split train[:500] | validation[:200]
  #   --limit 500
"""
import time, json, argparse, re
from datasets import load_dataset
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import requests
from tqdm import tqdm

def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return s

def bleu_rouge_best(hyp: str, refs):
    """Compute BLEU and ROUGE-L against multiple references, return the best pair."""
    hyp_norm = normalize_text(hyp)
    rouge = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    best_bleu, best_rouge = 0.0, 0.0
    for r in refs:
        r_norm = normalize_text(r)
        b = sentence_bleu([r_norm.split()], hyp_norm.split(),
                          smoothing_function=SmoothingFunction().method1)
        rr = rouge.score(r_norm, hyp_norm)['rougeL'].fmeasure
        if b + rr > best_bleu + best_rouge:
            best_bleu, best_rouge = b, rr
    return best_bleu, best_rouge

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="MCP server URL, e.g., http://localhost:8000/mcp")
    ap.add_argument("--out", required=True, help="Output JSON path, e.g., results/.../squad_eval.json")
    ap.add_argument("--split", default="validation[:200]", help="HF split (e.g., train, validation, validation[:200])")
    ap.add_argument("--limit", type=int, default=0, help="Optional cap on items (0=all in split)")
    ap.add_argument("--max_tokens", type=int, default=128)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top_p", type=float, default=0.9)
    args = ap.parse_args()

    ds = load_dataset("squad_v2", split=args.split)

    # Keep only answerable examples
    rows = [r for r in ds if not r.get("is_impossible", False)]
    if args.limit and args.limit > 0:
        rows = rows[:args.limit]

    rouge = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    results = []

    for r in tqdm(rows, desc="Evaluating SQuAD v2"):
        context = r["context"]
        question = r["question"]
        answers = r.get("answers", {}).get("text", [])
        if not answers:
            # Shouldn’t happen after filtering, but be safe
            continue

        prompt = (
            "You are a question answering assistant. Answer concisely using only the provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        start = time.time()
        try:
            resp = requests.post(args.url, json={
                "prompt": prompt,
                "max_tokens": args.max_tokens,
                "temperature": args.temperature,
                "top_p": args.top_p
            }, timeout=180)
            elapsed = (time.time() - start) * 1000.0
            resp.raise_for_status()
            output = resp.json().get("text", "").strip()
        except Exception as e:
            results.append({
                "question": question, "ref": answers, "out": "",
                "latency": None, "bleu": 0.0, "rouge": 0.0, "pass@1": 0,
                "error": str(e)
            })
            continue

        # Score vs multiple refs (best match)
        bleu, rougeL = bleu_rouge_best(output, answers)

        # Pass@1: strict normalized exact match against any reference
        out_norm = normalize_text(output)
        pass1 = int(any(out_norm == normalize_text(a) for a in answers))

        results.append({
            "question": question,
            "ref": answers,
            "out": output,
            "latency": round(elapsed, 2),
            "bleu": round(bleu, 4),
            "rouge": round(rougeL, 4),
            "pass@1": pass1
        })

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved SQuAD v2 eval to {args.out}  (n={len(results)})")

if __name__ == "__main__":
    main()
