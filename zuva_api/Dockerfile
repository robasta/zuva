FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY zuva_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy notification service code
COPY zuva_api/ /app/zuva_api/

# Run the service
CMD ["sh", "-c", "uvicorn zuva_api.main:app --host 0.0.0.0 --port 8001 --log-level ${UVICORN_LOG_LEVEL:-warning}"]
