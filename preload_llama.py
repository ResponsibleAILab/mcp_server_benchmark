#!/usr/bin/env python3
"""
Preloads the meta-llama/Llama-3.2-1B-Instruct model and tokenizer
into the Hugging Face cache before benchmarking begins.

Run this once before executing your benchmark scripts to ensure
all model weights and tokenizer files are available locally.

Requires a Hugging Face token with gated access.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"

print(f"Preloading {MODEL_ID} to local cache...")

# Set device to CPU for preload
device = torch.device("cpu")

# Load tokenizer and model to cache
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, token=True)

print("Model and tokenizer are now cached locally.")
