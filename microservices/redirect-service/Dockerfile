FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY redirect-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pydantic[email]

# Create shared directory
RUN mkdir -p /app/shared

# Copy the shared module
COPY shared/ /app/shared/

# Copy the service code
COPY redirect-service/app/database.py /app/app/
COPY redirect-service/app/main.py /app/app/

# Make sure the shared module is in Python path
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"] 