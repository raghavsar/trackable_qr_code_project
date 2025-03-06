FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY analytics-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pydantic[email] pydantic-settings

# Create shared directory
RUN mkdir -p /app/shared

# Copy the shared module
COPY shared/ /app/shared/

# Copy the entire app directory instead of individual files
COPY analytics-service/app /app/app/

# Set PYTHONPATH to just /app since we want app to be a package
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"] 