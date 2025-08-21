FROM python:3.11-slim

# ---- System deps ----
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates && rm -rf /var/lib/apt/lists/*

# ---- Application ----
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py /app/
COPY evaluate/evaluate_alpaca.py /app/
COPY evaluate/evaluate_boolq.py /app/
COPY evaluate/evaluate_squad.py /app/

EXPOSE 8000
ENV HF_TOKEN="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"
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]