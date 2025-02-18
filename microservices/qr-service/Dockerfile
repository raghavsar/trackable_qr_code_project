FROM python:3.11-slim

WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY qr-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pydantic[email]

# Copy the shared module
COPY shared /app/shared

# Copy the service code
COPY qr-service/app /app/app

# Create assets directory and copy logo
RUN mkdir -p /app/assets/images
COPY qr-service/test/test_output/Phonon_Favicon.png /app/assets/images/phonon-favicon.png

# Make sure the shared module is in Python path
ENV PYTHONPATH=/app

# Create __init__.py if it doesn't exist
RUN touch /app/shared/__init__.py

# Verify Python can find the module
RUN python3 -c "import sys; print('Python path:', sys.path); import shared.models; print('Models found')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"] 