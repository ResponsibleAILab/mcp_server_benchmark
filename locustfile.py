"""Locust workload generator for MCP latency/throughput tests."""
from locust import HttpUser, task, between
import json, random, string


def random_prompt(n: int = 24):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


class MCPUser(HttpUser):
    wait_time = between(0.1, 0.3)  # steady‑state load

    @task
    def invoke_mcp(self):
        payload = {"prompt": random_prompt()}
        self.client.post("/mcp", json=payload, name="/mcp")