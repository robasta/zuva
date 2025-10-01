"""
Sunsynk Solar Dashboard - Phase 3 Backend API
FastAPI backend with WebSocket support for real-time solar monitoring
"""

import os
import sys
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
import aiohttp

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

# Add the sunsynk package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import Sunsynk client
from sunsynk.client import SunsynkClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer()

# Password hashing - simple hash for demo
import hashlib

def hash_password(password: str) -> str:
    """Simple password hashing for demo purposes"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hash_password(plain_password) == hashed_password

# Demo user credentials (in production, use proper user management)
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "password": hash_password("admin123"),
        "roles": ["admin", "user"]
    },
    "demo": {
        "username": "demo", 
        "password": hash_password("demo123"),
        "roles": ["user"]
    }
}

# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class DashboardMetrics(BaseModel):
    timestamp: datetime
    solar_power: float
    battery_level: float
    grid_power: float
    consumption: float
    weather_condition: str
    temperature: float

class SystemStatus(BaseModel):
    online: bool
    last_update: datetime
    inverter_status: str
    battery_status: str
    grid_status: str

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[Any, Any]

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Background tasks
class RealSunsynkCollector:
    """Real Sunsynk data collector integrated into the backend."""
    
    def __init__(self):
        # Real credentials
        self.username = 'robert.dondo@gmail.com'
        self.password = 'M%TcEJvo9^j8di'
        self.weather_key = '8c0021a3bea8254c109a414d2efaf9d6'
        self.location = 'Randburg,ZA'
        
        self.latest_data = None
        self.last_update = None
        
    async def collect_weather_data(self):
        """Collect weather data from OpenWeatherMap."""
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.location,
                'appid': self.weather_key,
                'units': 'metric'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    return {
                        'temperature': data['main']['temp'],
                        'humidity': data['main']['humidity'],
                        'cloud_cover': data['clouds']['all'],
                        'weather_condition': data['weather'][0]['main'].lower(),
                        'description': data['weather'][0]['description']
                    }
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {
                'temperature': 22.0,
                'humidity': 60,
                'cloud_cover': 20,
                'weather_condition': 'unknown',
                'description': 'Weather data unavailable'
            }
    
    async def collect_sunsynk_data(self, client, inverter_sn):
        """Collect real-time data from Sunsynk inverter."""
        try:
            # Get real-time data
            battery = await client.get_inverter_realtime_battery(inverter_sn)
            grid = await client.get_inverter_realtime_grid(inverter_sn)
            input_data = await client.get_inverter_realtime_input(inverter_sn)
            output = await client.get_inverter_realtime_output(inverter_sn)
            
            # Convert watts to kilowatts and handle data types
            solar_power = float(input_data.get_power()) / 1000  # W to kW
            battery_power = float(battery.get_power()) / 1000   # W to kW  
            grid_power = float(grid.get_power()) / 1000         # W to kW
            consumption = float(getattr(output, 'pac', 0)) / 1000  # W to kW
            battery_soc = float(battery.soc)
            
            return {
                'solar_power': round(solar_power, 3),
                'battery_power': round(battery_power, 3),
                'grid_power': round(grid_power, 3),
                'consumption': round(consumption, 3),
                'battery_soc': round(battery_soc, 1),
                'battery_voltage': round(float(battery.get_voltage()), 1),
                'grid_voltage': round(float(grid.get_voltage()), 1),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Sunsynk data collection error: {e}")
            return None
    
    async def run_collection_cycle(self):
        """Run a single data collection cycle."""
        try:
            async with SunsynkClient(self.username, self.password) as client:
                # Get inverter
                inverters = await client.get_inverters()
                if not inverters:
                    logger.error("No inverters found")
                    return False
                    
                inverter = inverters[0]
                inverter_sn = inverter.sn
                
                # Collect data
                solar_data = await self.collect_sunsynk_data(client, inverter_sn)
                weather_data = await self.collect_weather_data()
                
                if not solar_data:
                    logger.error("Failed to collect solar data")
                    return False
                
                # Store the latest data
                self.latest_data = {
                    'solar_data': solar_data,
                    'weather_data': weather_data,
                    'timestamp': datetime.now()
                }
                self.last_update = datetime.now()
                
                logger.info(f"✅ Real data collected: Solar {solar_data['solar_power']}kW, Battery {solar_data['battery_soc']}%, Grid {solar_data['grid_power']}kW")
                
                return True
                
        except Exception as e:
            logger.error(f"Collection cycle error: {e}")
            return False
    
    def get_current_data(self):
        """Get the latest collected data."""
        if not self.latest_data:
            return None
            
        solar = self.latest_data['solar_data']
        weather = self.latest_data['weather_data']
        
        return {
            'metrics': {
                'timestamp': solar['timestamp'],
                'solar_power': solar['solar_power'],
                'battery_level': solar['battery_soc'],
                'grid_power': solar['grid_power'],
                'consumption': solar['consumption'],
                'weather_condition': weather['weather_condition'],
                'temperature': weather['temperature']
            },
            'status': {
                'online': True,
                'last_update': self.last_update,
                'inverter_status': 'online',
                'battery_status': 'normal' if solar['battery_soc'] > 20 else 'low',
                'grid_status': 'connected'
            }
        }

# Global collector instance
real_collector = RealSunsynkCollector()

class BackgroundTasks:
    def __init__(self):
        self.running = False
        self.tasks = []

    async def start_background_tasks(self):
        if self.running:
            return
        
        self.running = True
        logger.info("Starting background tasks...")
        
        # Start real data collection task
        task = asyncio.create_task(self.generate_real_data())
        self.tasks.append(task)

    async def stop_background_tasks(self):
        self.running = False
        logger.info("Stopping background tasks...")
        
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()

    async def generate_real_data(self):
        """Collect real Sunsynk data and broadcast to WebSocket clients"""
        logger.info("🚀 Starting real Sunsynk data collection...")
        
        while self.running:
            try:
                # Collect real data
                success = await real_collector.run_collection_cycle()
                
                if success:
                    # Get the current data
                    current_data = real_collector.get_current_data()
                    
                    if current_data:
                        # Broadcast to WebSocket clients
                        dashboard_message = WebSocketMessage(
                            type="dashboard_update",
                            data=current_data
                        )
                        
                        await manager.broadcast(dashboard_message.model_dump_json())
                        logger.debug("📡 Real data broadcasted to WebSocket clients")
                else:
                    logger.warning("⚠️ Failed to collect real data, retrying...")
                
                # Wait before next update (30 seconds for real data)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in real data collection: {e}")
                await asyncio.sleep(60)  # Wait longer on error

background_tasks = BackgroundTasks()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Sunsynk Dashboard API...")
    await background_tasks.start_background_tasks()
    yield
    # Shutdown
    logger.info("Shutting down Sunsynk Dashboard API...")
    await background_tasks.stop_background_tasks()

# FastAPI app initialization
app = FastAPI(
    title="Sunsynk Solar Dashboard API",
    description="Professional solar monitoring API with real-time WebSocket support",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication helpers removed - using direct verify_password function

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# API Routes
@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "3.0.0",
        "services": {
            "api": "online",
            "websocket": "online",
            "background_tasks": background_tasks.running
        }
    }

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """User authentication endpoint"""
    user = DEMO_USERS.get(login_data.username)
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["username"], "roles": user["roles"]}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )

@app.get("/api/dashboard/current")
async def get_current_dashboard_data(user: dict = Depends(verify_token)):
    """Get current dashboard metrics from real Sunsynk data"""
    
    # Try to get real data first
    current_data = real_collector.get_current_data()
    
    if current_data:
        return current_data
    
    # Fallback to collecting fresh data if no cached data
    try:
        success = await real_collector.run_collection_cycle()
        if success:
            current_data = real_collector.get_current_data()
            if current_data:
                return current_data
    except Exception as e:
        logger.error(f"Failed to collect fresh data: {e}")
    
    # Ultimate fallback - return error status
    now = datetime.now()
    return {
        "metrics": {
            "timestamp": now,
            "solar_power": 0.0,
            "battery_level": 0.0,
            "grid_power": 0.0,
            "consumption": 0.0,
            "weather_condition": "unknown",
            "temperature": 0.0
        },
        "status": {
            "online": False,
            "last_update": now,
            "inverter_status": "offline",
            "battery_status": "unknown",
            "grid_status": "disconnected"
        }
    }

@app.get("/api/dashboard/history")
async def get_dashboard_history(
    hours: int = 24,
    user: dict = Depends(verify_token)
):
    """Get historical dashboard data"""
    now = datetime.now()
    history = []
    
    for i in range(hours):
        timestamp = now - timedelta(hours=hours-i)
        hour = timestamp.hour
        
        # Generate historical data
        import random
        import math
        
        if 6 <= hour <= 18:
            solar_factor = math.sin(math.pi * (hour - 6) / 12)
            base_solar = 4.5 * solar_factor
            solar_power = max(0, base_solar + random.uniform(-0.3, 0.3))
        else:
            solar_power = 0.0
        
        battery_level = 50 + 25 * math.sin(math.pi * hour / 12) + random.uniform(-3, 3)
        battery_level = max(10, min(100, battery_level))
        
        consumption = 1.5 + random.uniform(-0.2, 0.6)
        grid_power = consumption - solar_power
        
        history.append({
            "timestamp": timestamp,
            "solar_power": round(solar_power, 2),
            "battery_level": round(battery_level, 1),
            "grid_power": round(grid_power, 2),
            "consumption": round(consumption, 2)
        })
    
    return {"history": history}

@app.get("/api/analytics/predictions")
async def get_predictions(user: dict = Depends(verify_token)):
    """Get ML predictions (demo data)"""
    now = datetime.now()
    predictions = []
    
    # Generate 24-hour predictions
    for i in range(24):
        timestamp = now + timedelta(hours=i)
        hour = timestamp.hour
        
        import random
        import math
        
        # Predict solar generation
        if 6 <= hour <= 18:
            solar_factor = math.sin(math.pi * (hour - 6) / 12)
            predicted_solar = 4.5 * solar_factor + random.uniform(-0.2, 0.2)
        else:
            predicted_solar = 0.0
        
        # Predict consumption based on typical patterns
        if 6 <= hour <= 8 or 17 <= hour <= 22:  # Morning and evening peaks
            predicted_consumption = 2.0 + random.uniform(-0.3, 0.5)
        else:
            predicted_consumption = 1.2 + random.uniform(-0.2, 0.4)
        
        predictions.append({
            "timestamp": timestamp,
            "predicted_solar": round(max(0, predicted_solar), 2),
            "predicted_consumption": round(predicted_consumption, 2),
            "confidence": round(random.uniform(0.7, 0.95), 2)
        })
    
    return {
        "predictions": predictions,
        "model_last_trained": now - timedelta(hours=2),
        "model_accuracy": 0.89
    }

@app.get("/api/analytics/optimization")
async def get_optimization_recommendations(user: dict = Depends(verify_token)):
    """Get battery optimization recommendations"""
    recommendations = [
        {
            "type": "charge_schedule",
            "title": "Optimal Charging Schedule",
            "description": "Charge battery during peak solar hours (10:00-14:00)",
            "impact": "15% efficiency improvement",
            "priority": "high"
        },
        {
            "type": "load_shifting",
            "title": "Load Shifting Opportunity",
            "description": "Shift heavy appliance usage to solar peak hours",
            "impact": "R150/month savings",
            "priority": "medium"
        },
        {
            "type": "export_optimization",
            "title": "Grid Export Timing",
            "description": "Export excess power during high tariff periods (18:00-20:00)",
            "impact": "R200/month additional income",
            "priority": "high"
        }
    ]
    
    return {"recommendations": recommendations}

# WebSocket endpoint
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True
    )
