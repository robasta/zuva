FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install base sunsynk client first
COPY .git /app/.git
COPY sunsynk /app/sunsynk
COPY setup.py /app/
COPY requirements.txt /app/
RUN pip install --no-cache-dir -e .

# Copy collector requirements and install
COPY zuva/collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy collector code
COPY zuva/collector/ /app/collector/

# Set Python path to include all directories
ENV PYTHONPATH="/app:/app/collector"

# Create logs directory
RUN mkdir -p /app/logs

# Run the alert monitor
CMD ["python", "-m", "collector.alert_monitor"]