FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the parent sunsynk module
COPY ../sunsynk /app/sunsynk/

# Copy collector source code
COPY . /app/collector/

# Copy analytics module
COPY ../analytics /app/analytics/

# Set Python path to include all directories
ENV PYTHONPATH="/app:/app/collector:/app/analytics"

# Create logs directory
RUN mkdir -p /app/logs

# Set up non-root user for security
RUN useradd --create-home --shell /bin/bash collector
RUN chown -R collector:collector /app
USER collector

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from models import system_health; print('healthy' if system_health.is_healthy() else exit(1))"

# Run the data collector
CMD ["python", "/app/collector/data_collector.py"]