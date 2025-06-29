"""Minimal MCP‑style FastAPI server for bare‑metal benchmark."""
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