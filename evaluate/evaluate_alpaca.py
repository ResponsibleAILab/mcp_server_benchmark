"""
Evaluate LLM via MCP on Alpaca dataset.
Logs latency, BLEU, ROUGE, and Pass@1 to a JSON output file.
"""
import time, json, argparse
from datasets import load_dataset
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import requests
from tqdm import tqdm

def score(output, reference):
    bleu = sentence_bleu([reference.split()], output.split(), smoothing_function=SmoothingFunction().method1)
    rouge = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    rouge_score = rouge.score(reference, output)['rougeL'].fmeasure
    pass_at_1 = int(output.strip().lower() == reference.strip().lower())
    return bleu, rouge_score, pass_at_1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="MCP server URL")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()

    dataset = load_dataset("tatsu-lab/alpaca", split="train[:500]")  # Small test set for now

    results = []
    for row in tqdm(dataset, desc="Evaluating"):
        prompt = row["instruction"] + "\n" + row.get("input", "")
        reference = row["output"]

        start = time.time()
        try:
            resp = requests.post(args.url, json={"prompt": prompt})
            elapsed = time.time() - start
            if resp.status_code != 200:
                raise ValueError(f"Status {resp.status_code}")
            output = resp.json().get("text", "")
        except Exception as e:
            results.append({"error": str(e), "latency": None, "bleu": 0, "rouge": 0, "pass@1": 0})
            continue

        bleu, rouge, pass1 = score(output, reference)
        results.append({
            "prompt": prompt, "ref": reference, "out": output,
            "latency": round(elapsed * 1000, 2),  # ms
            "bleu": round(bleu, 4), "rouge": round(rouge, 4),
            "pass@1": pass1
        })

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved eval results to {args.out}")

if __name__ == "__main__":
    main()