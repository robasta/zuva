#!/usr/bin/env bash

set -euo pipefail

SERVER_HOST="${SERVER_HOST:-robasta@192.168.1.42}"
REMOTE_DASHBOARD_DIR="${REMOTE_DASHBOARD_DIR:-/home/robasta/docker/zuva}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
USE_SUDO="${USE_SUDO:-true}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_COMPOSE_PATH="${SCRIPT_DIR}/${COMPOSE_FILE}"

if [[ ! -f "${LOCAL_COMPOSE_PATH}" ]]; then
  echo "Error: compose file not found at ${LOCAL_COMPOSE_PATH}"
  exit 1
fi

echo "Copying ${COMPOSE_FILE} to ${SERVER_HOST}:${REMOTE_DASHBOARD_DIR}/"
ssh "${SERVER_HOST}" "mkdir -p '${REMOTE_DASHBOARD_DIR}'"
rsync -az "${LOCAL_COMPOSE_PATH}" "${SERVER_HOST}:${REMOTE_DASHBOARD_DIR}/${COMPOSE_FILE}"

if [[ "${USE_SUDO}" == "true" ]]; then
  DOCKER_CMD="sudo docker"
else
  DOCKER_CMD="docker"
fi

echo "Running docker compose pull and up -d on ${SERVER_HOST}"
ssh "${SERVER_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && ${DOCKER_CMD} compose -f '${COMPOSE_FILE}' pull && ${DOCKER_CMD} compose -f '${COMPOSE_FILE}' up -d"

echo "Deployment complete"
ssh "${SERVER_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && ${DOCKER_CMD} compose -f '${COMPOSE_FILE}' ps"
