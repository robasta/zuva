FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY notification_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy notification service code
COPY notification_service/ /app/notification_service/

# Run the service
CMD ["python", "-m", "notification_service.main"]
