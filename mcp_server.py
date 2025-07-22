"""
MCP server that wraps meta-llama/Llama-3.2-1B-Instruct
and exposes /mcp for the benchmarking harness.
"""
import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"
HF_TOKEN = "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" # os.environ.get("HF_TOKEN")

if HF_TOKEN is None:
    raise RuntimeError("Missing Hugging Face token – please set HF_TOKEN env variable")
else:
    print("Token Found!")

# ---------- load model & tokenizer ----------
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

print("Beginning Tokenizer")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    torch_dtype="auto",
    device_map=device
)
model.eval()
print("Model Eval Complete")
app = FastAPI(title="MCP – Llama-3.2-1B-Instruct")

class Prompt(BaseModel):
    prompt: str
    max_tokens: int = 128
    temperature: float = 0.7
    top_p: float = 0.9

# ---------- helper ----------
def format_prompt(user_msg: str) -> str:
    # LLama-3.2-1B-Instruct follows the chat-instruction template
    return f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{user_msg}\n<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"

# ---------- endpoint ----------
@app.post("/mcp")
async def mcp_endpoint(p: Prompt):
    try:
        prompt_text = format_prompt(p.prompt)
        inputs      = tokenizer(prompt_text, return_tensors="pt").to(device)
        outputs     = model.generate(
            **inputs,
            max_new_tokens=p.max_tokens,
            temperature=p.temperature,
            top_p=p.top_p,
            do_sample=True,
            eos_token_id=tokenizer.eos_token_id,
        )
        full = tokenizer.decode(outputs[0], skip_special_tokens=True)
        # keep only the assistant part
        answer = full.split("assistant")[-1].strip()
        return {"text": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)

"""Minimal MCP‑style FastAPI server for bare‑metal benchmark.
from fastapi import FastAPI, Request
import uvicorn
import time

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(req: Request):
    body = await req.json()
    # Simulate small (5 ms) model/context processing delay
    time.sleep(0.015)
    return {"response": f"echo: {body.get('prompt', '')}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)
"""