FROM python:3.11-slim

# ---- System deps ----
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
        ca-certificates && rm -rf /var/lib/apt/lists/*

# ---- Application ----
WORKDIR /app
COPY mcp_server.py /app/
RUN pip install --no-cache-dir fastapi uvicorn "uvicorn[standard]" psutil

EXPOSE 8000
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]