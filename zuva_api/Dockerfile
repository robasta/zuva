FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY zuva_api/requirements.txt .
RUN pip install -r requirements.txt

COPY zuva_api/ /app/zuva_api/

# User settings and rate-limit state live in SQLite here. Mount a volume on
# /data or every restart forgets which chat to notify.
RUN mkdir -p /data
ENV SETTINGS_DB_PATH=/data/zuva.db

# No curl or wget in the slim image, and /health is unauthenticated by design.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4)"

CMD ["sh", "-c", "uvicorn zuva_api.main:app --host 0.0.0.0 --port 8001 --log-level ${UVICORN_LOG_LEVEL:-warning}"]
