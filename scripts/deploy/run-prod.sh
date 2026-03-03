#!/usr/bin/env bash

set -euo pipefail

SERVER_HOST="${SERVER_HOST:-robasta@192.168.1.42}"
REMOTE_DASHBOARD_DIR="${REMOTE_DASHBOARD_DIR:-/home/robasta/docker/zuva}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
USE_SUDO="${USE_SUDO:-true}"

if [[ "${USE_SUDO}" == "true" ]]; then
  DOCKER_CMD="sudo docker"
  SSH_CMD=(ssh -tt)
else
  DOCKER_CMD="docker"
  SSH_CMD=(ssh)
fi

echo "Running docker compose pull and up -d on ${SERVER_HOST}"
"${SSH_CMD[@]}" "${SERVER_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && ${DOCKER_CMD} compose -f '${COMPOSE_FILE}' pull && ${DOCKER_CMD} compose -f '${COMPOSE_FILE}' up -d"

echo "Deployment complete"
"${SSH_CMD[@]}" "${SERVER_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && ${DOCKER_CMD} compose -f '${COMPOSE_FILE}' ps"
