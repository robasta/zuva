#!/bin/bash
# Sunsynk Dashboard Quick Start Script - Phase 3

echo "🌞 Starting Sunsynk Dashboard - Phase 3 (Real Data Integration)"
echo "================================================================="

# Check if in correct directory
if [ ! -d "sunsynk-dashboard" ]; then
    echo "❌ Error: Please run from the sunsynk-api-client-main directory"
    exit 1
fi

# Set Python path
export PYTHONPATH=$(pwd)

echo "📊 Phase 3 Features:"
echo "✅ Real Sunsynk API integration"
echo "✅ Live battery SOC (92-94%)"
echo "✅ Actual power generation/consumption"
echo "✅ Real weather data"
echo "✅ 30-second live updates"
echo ""

# Function to start backend
start_backend() {
    echo "🚀 Starting backend API (FastAPI with real Sunsynk data)..."
    cd sunsynk-dashboard/backend
    
    # Check if dependencies are installed
    if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
        echo "📦 Installing FastAPI dependencies..."
        python3 -m pip install fastapi uvicorn pydantic pyjwt python-multipart aiohttp
    fi
    
    echo "🔗 Starting backend on http://localhost:8000"
    echo "📈 Real data collection every 30 seconds..."
    echo ""
    
    # Start backend
    python3 main.py &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 3
    
    # Test backend health
    if curl -s http://localhost:8000/api/health > /dev/null; then
        echo "✅ Backend started successfully!"
    else
        echo "❌ Backend failed to start"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    
    cd ../..
}

# Function to start frontend
start_frontend() {
    echo "🎨 Starting simple frontend dashboard..."
    cd sunsynk-dashboard/simple-frontend
    
    echo "🌐 Starting frontend on http://localhost:3000"
    echo ""
    
    # Start frontend in background
    python3 -m http.server 3000 > /dev/null 2>&1 &
    FRONTEND_PID=$!
    
    # Wait for frontend to start
    sleep 2
    
    # Test frontend
    if curl -s http://localhost:3000 > /dev/null; then
        echo "✅ Frontend started successfully!"
    else
        echo "❌ Frontend failed to start"
        kill $FRONTEND_PID 2>/dev/null
        exit 1
    fi
    
    cd ../..
}

# Start services
start_backend
start_frontend

echo ""
echo "🎉 Sunsynk Dashboard Phase 3 is now running!"
echo "================================================================="
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "💊 Health Check: http://localhost:8000/api/health"
echo ""
echo "🔐 Login credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📈 Real Data Features:"
echo "   ✅ Live inverter data (2305156257)"
echo "   ✅ Real battery SOC (92-94%)"
echo "   ✅ Actual solar generation"
echo "   ✅ Weather from Randburg, ZA"
echo "   ✅ 30-second auto-refresh"
echo ""
echo "🛑 To stop: Press Ctrl+C or run: pkill -f 'python3 main.py' && pkill -f 'python3 -m http.server'"
echo ""

# Keep script running and show live logs
echo "📊 Live backend logs (Ctrl+C to stop):"
echo "======================================="
wait
