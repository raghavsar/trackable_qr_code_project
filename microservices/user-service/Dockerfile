FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements first
COPY user-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the user-service contents to /app
COPY user-service/ .

# Create __init__.py if it doesn't exist
RUN touch __init__.py

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]