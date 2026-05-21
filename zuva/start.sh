#!/bin/bash

# Sunsynk Notification System Startup Script

set -e

COMPOSE_CMD=(docker compose --env-file .env -f ../docker-compose.yml)

echo "🔔 Starting Sunsynk Notification System..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please copy .env.template to .env and configure your credentials"
    echo "   cp .env.template .env"
    exit 1
fi

# Check for required environment variables
source .env

if [ -z "$SUNSYNK_USERNAME" ] || [ -z "$SUNSYNK_PASSWORD" ]; then
    echo "❌ Error: SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set in .env"
    exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ] && [ -z "$TWILIO_ACCOUNT_SID" ]; then
    echo "⚠️  Warning: No notification channels configured!"
    echo "   Set TELEGRAM_BOT_TOKEN and/or TWILIO credentials in .env"
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
"${COMPOSE_CMD[@]}" down 2>/dev/null || true

# Pull latest images
echo "📦 Pulling Docker images..."
"${COMPOSE_CMD[@]}" pull

# Start services
echo "🚀 Starting services..."
"${COMPOSE_CMD[@]}" up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check service health
echo "🏥 Checking service health..."
"${COMPOSE_CMD[@]}" ps

# Show logs
echo ""
echo "✅ System started successfully!"
echo ""
echo "📊 Service URLs:"
echo "   - Notification API: http://localhost:8001"
echo "   - API Health: http://localhost:8001/health"
echo "   - InfluxDB: http://localhost:8086"
echo ""
echo "📝 View logs with: docker compose --env-file .env -f ../docker-compose.yml logs -f"
echo "🛑 Stop system with: docker compose --env-file .env -f ../docker-compose.yml down"
echo ""
echo "🔔 Your notification system is now monitoring your Sunsynk inverter!"
