FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY analytics-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pydantic[email]

# Create shared directory
RUN mkdir -p /app/shared

# Copy the shared module
COPY shared/ /app/shared/

# Copy the service code
COPY analytics-service/app/auth.py /app/app/
COPY analytics-service/app/database.py /app/app/
COPY analytics-service/app/main.py /app/app/
COPY analytics-service/app/redis_store.py /app/app/
COPY analytics-service/app/__init__.py /app/app/

# Make sure the shared module is in Python path
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"] 