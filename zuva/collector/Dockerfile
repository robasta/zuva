FROM python:3.11-slim

# Stamped in by the build so setup.py does not need the repository history or a
# git binary to work out a version.
ARG SUNSYNK_API_CLIENT_VERSION=0.0.0

ENV SUNSYNK_API_CLIENT_VERSION=${SUNSYNK_API_CLIENT_VERSION} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Every pinned dependency publishes a wheel for this platform, so no gcc /
# build-essential toolchain is installed.
COPY zuva/collector/requirements.txt /app/requirements-collector.txt
RUN pip install -r /app/requirements-collector.txt

# --no-deps: requirements-collector.txt already pins what the client needs, and
# resolving setup.py's requirements again would pull dev-only extras.
COPY requirements.txt setup.py /app/
COPY sunsynk /app/sunsynk
RUN pip install --no-deps -e .

COPY zuva/collector/ /app/collector/

ENV PYTHONPATH="/app:/app/collector"

# Suppression state lives here so a restart does not re-send every alert.
RUN mkdir -p /data
ENV COLLECTOR_STATE_PATH=/data/collector-state.json

# The monitor listens on no port. It touches a heartbeat file after each
# completed poll; collector.heartbeat exits non-zero once that goes stale, which
# catches a wedged poll loop that a process check would call healthy.
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python -m collector.heartbeat

CMD ["python", "-m", "collector.orchestrator"]
