#!/bin/bash
# Starts the local development stack (builds from this checkout).
# The deployed stack is scripts/deploy/docker-compose.prod.yml, uploaded to
# Portainer by hand - this script is not used for it.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
COMPOSE_CMD=(docker compose --env-file "$ENV_FILE" -f "$REPO_ROOT/docker-compose.yml")

echo "🔔 Starting Sunsynk Notification System..."

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    echo "📝 Copy the template and fill in your credentials:"
    echo "   cp zuva/.env.template .env"
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [ -z "$SUNSYNK_USERNAME" ] || [ -z "$SUNSYNK_PASSWORD" ]; then
    echo "❌ Error: SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set in .env"
    exit 1
fi

if [ -z "$ZUVA_API_KEY" ]; then
    # The compose file falls back to a dev key so this still runs locally, but
    # the collector and API must agree on the value.
    echo "⚠️  Warning: ZUVA_API_KEY is not set; using the local dev default."
    echo "   Generate a real one for anything exposed: openssl rand -hex 32"
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  Warning: TELEGRAM_BOT_TOKEN is not set - alerts will be evaluated"
    echo "   and stored, but nothing will be delivered."
fi

echo "🛑 Stopping existing containers..."
"${COMPOSE_CMD[@]}" down 2>/dev/null || true

echo "🔨 Building images..."
"${COMPOSE_CMD[@]}" build

echo "🚀 Starting services..."
"${COMPOSE_CMD[@]}" up -d

echo "⏳ Waiting for services to become healthy..."
sleep 10

echo "🏥 Checking service health..."
"${COMPOSE_CMD[@]}" ps

echo ""
echo "✅ System started."
echo ""
echo "📊 Service URLs:"
echo "   - Notification API: http://localhost:8001"
echo "   - API Health:       http://localhost:8001/health  (no API key needed)"
echo "   - InfluxDB:         http://127.0.0.1:8086         (loopback only)"
echo ""
echo "   Other endpoints need a header: -H \"X-API-Key: \$ZUVA_API_KEY\""
echo ""
echo "📝 Logs: ${COMPOSE_CMD[*]} logs -f"
echo "🛑 Stop: ${COMPOSE_CMD[*]} down"
