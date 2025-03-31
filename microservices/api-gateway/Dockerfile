FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY api-gateway/main.py /app/
COPY api-gateway/circuit_breaker.py /app/
COPY api-gateway/config.py /app/

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
