FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY vcard-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create shared directory
RUN mkdir -p /app/shared

# Copy the shared module
COPY shared/ /app/shared/

# Copy the service code
COPY vcard-service/app/auth.py /app/app/
COPY vcard-service/app/database.py /app/app/
COPY vcard-service/app/main.py /app/app/

# Make sure the shared module is in Python path
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"] 