"""Locust workload generator for LLaMA-3.2-1B-Instruct MCP latency/throughput tests."""
from locust import HttpUser, task, between
import random

# Example realistic prompts
PROMPT_POOL = [
    "What is the capital of Germany?",
    "Explain the Doppler effect.",
    "Write a short poem about space exploration.",
    "How does a neural network learn?",
    "Give an example of a bubble sort algorithm in Python.",
    "Translate 'Good morning' into French.",
    "What is Newton's second law of motion?",
    "Summarize the plot of Romeo and Juliet.",
    "What are the benefits of containerization in software development?",
    "What is the difference between supervised and unsupervised learning?"
]

class MCPUser(HttpUser):
    wait_time = between(0.1, 0.3)  # Maintain load over time

    @task
    def invoke_mcp(self):
        prompt = random.choice(PROMPT_POOL)
        payload = {
            "prompt": prompt,
            "max_tokens": 128,
            "temperature": 0.7,
            "top_p": 0.9
        }
        self.client.post("/mcp", json=payload, name="/mcp")