FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY zuva_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy notification service code
COPY zuva_api/ /app/zuva_api/

# Run the service
CMD ["python", "-m", "zuva_api.main"]
