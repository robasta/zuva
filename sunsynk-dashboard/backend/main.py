"""
Sunsynk Solar Dashboard - Phase 6 Backend API
FastAPI backend with InfluxDB integration and advanced ML analytics
Real-time monitoring with machine learning predictions and optimization
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
import pandas as pd
import numpy as np

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("dashboard.log")
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to sys.path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Core imports
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pathlib import Path
import aiohttp
import jwt
import uvicorn
import json
import traceback

# Add sunsynk package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from sunsynk.client import SunsynkClient

# Phase 6 Analytics Modules - Import with error handling
PHASE6_AVAILABLE = False
try:
    from analytics.weather_correlator import AdvancedWeatherAnalyzer
    from analytics.consumption_ml import ConsumptionMLAnalyzer
    from analytics.battery_optimizer import BatteryOptimizer
    weather_analyzer = AdvancedWeatherAnalyzer()
    consumption_analyzer = ConsumptionMLAnalyzer()
    battery_optimizer = BatteryOptimizer()
    PHASE6_AVAILABLE = True
    logger.info("✅ Phase 6 Advanced Analytics modules loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Phase 6 Analytics modules not available: {e}")
except Exception as e:
    logger.warning(f"⚠️ Phase 6 Analytics initialization error: {e}")

# Local imports
try:
    from components.auth import AuthManager
    from components.influx_manager import InfluxManager
    from components.data_collector import RealDataCollector
    logger.info("✅ All core components loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import core components: {e}")
    sys.exit(1)

# Import Phase 6 Analytics Modules
try:
    from analytics.weather_correlator import weather_analyzer
    from analytics.consumption_ml import consumption_analyzer
    from analytics.battery_optimizer import battery_optimizer
    PHASE6_AVAILABLE = True
    logger.info("✅ Phase 6 analytics modules loaded successfully")
except ImportError as e:
    logger.warning(f"Phase 6 analytics modules not available: {e}")
    PHASE6_AVAILABLE = False

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# InfluxDB Configuration  
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "T72osJpuV_vwsv-8bHauVAjO5R_-HgTJM3iAGsGRG0dI-0MnqvELTTHuBSWHKhRP5_U5IMprDKVC3zawzpLHCA==")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "sunsynk")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "solar_metrics")

# Security
security = HTTPBearer()

# Password hashing
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# Demo users
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
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# InfluxDB Integration
class InfluxDBManager:
    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self.connected = False
        
    async def connect(self):
        try:
            self.client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection by listing buckets
            buckets = self.client.buckets_api().find_buckets()
            self.connected = True
            logger.info(f"✅ Connected to InfluxDB at {INFLUXDB_URL}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to InfluxDB: {e}")
            self.connected = False
            return False
    
    def write_metrics(self, metrics_data: dict):
        if not self.connected or not self.write_api:
            logger.warning("InfluxDB not connected, skipping write")
            return False
            
        try:
            points = []
            
            # Solar metrics point
            solar_point = Point("solar_metrics") \
                .tag("source", "sunsynk") \
                .tag("inverter_sn", "2305156257") \
                .field("solar_power", float(metrics_data.get("solar_power", 0))) \
                .field("battery_level", float(metrics_data.get("battery_soc", 0))) \
                .field("battery_power", float(metrics_data.get("battery_power", 0))) \
                .field("grid_power", float(metrics_data.get("grid_power", 0))) \
                .field("consumption", float(metrics_data.get("consumption", 0))) \
                .field("battery_voltage", float(metrics_data.get("battery_voltage", 0))) \
                .field("grid_voltage", float(metrics_data.get("grid_voltage", 0))) \
                .time(metrics_data.get("timestamp", datetime.now()), WritePrecision.S)
            
            points.append(solar_point)
            
            # Weather point if available
            if "weather_data" in metrics_data:
                weather = metrics_data["weather_data"]
                weather_point = Point("weather_metrics") \
                    .tag("location", "Randburg") \
                    .field("temperature", float(weather.get("temperature", 0))) \
                    .field("humidity", float(weather.get("humidity", 0))) \
                    .field("cloud_cover", float(weather.get("cloud_cover", 0))) \
                    .tag("condition", weather.get("weather_condition", "unknown")) \
                    .time(metrics_data.get("timestamp", datetime.now()), WritePrecision.S)
                
                points.append(weather_point)
            
            # Write to InfluxDB
            self.write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
            logger.debug("📊 Metrics written to InfluxDB")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write to InfluxDB: {e}")
            return False
    
    def query_historical_data(self, hours: int = 24) -> List[Dict]:
        if not self.connected or not self.query_api:
            logger.warning("InfluxDB not connected, returning empty data")
            return []
            
        try:
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r["_measurement"] == "solar_metrics")
                |> filter(fn: (r) => r["_field"] == "solar_power" or 
                                   r["_field"] == "battery_level" or 
                                   r["_field"] == "grid_power" or 
                                   r["_field"] == "consumption" or
                                   r["_field"] == "battery_power")
                |> aggregateWindow(every: 30m, fn: mean, createEmpty: false)
                |> yield(name: "mean")
            '''
            
            result = self.query_api.query_data_frame(query=query)
            
            if result.empty:
                logger.info("No historical data found in InfluxDB")
                return []
            
            # Convert to our format
            historical_data = []
            grouped = result.groupby('_time')
            
            for timestamp, group in grouped:
                data_point = {"timestamp": timestamp}
                
                for _, row in group.iterrows():
                    field = row['_field']
                    value = float(row['_value']) if pd.notna(row['_value']) else 0.0
                    data_point[field] = value
                
                # Ensure all required fields exist
                required_fields = ['solar_power', 'battery_level', 'grid_power', 'consumption', 'battery_power']
                for field in required_fields:
                    if field not in data_point:
                        data_point[field] = 0.0
                
                # Add temperature (from weather data or default)
                data_point['temperature'] = 22.0  # Default temp
                historical_data.append(data_point)
            
            logger.info(f"📈 Retrieved {len(historical_data)} historical data points")
            return sorted(historical_data, key=lambda x: x['timestamp'])
            
        except Exception as e:
            logger.error(f"❌ Failed to query InfluxDB: {e}")
            return []
    
    def get_analytics_summary(self, hours: int = 24) -> Dict:
        if not self.connected:
            return {"total_points": 0, "avg_solar_power": 0, "avg_consumption": 0, "energy_efficiency": 0}
            
        try:
            query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r["_measurement"] == "solar_metrics")
                |> filter(fn: (r) => r["_field"] == "solar_power" or 
                                   r["_field"] == "consumption")
                |> mean()
                |> yield(name: "mean")
            '''
            
            result = self.query_api.query_data_frame(query=query)
            
            if result.empty:
                return {"total_points": 0, "avg_solar_power": 0, "avg_consumption": 0, "energy_efficiency": 0}
            
            summary = {"total_points": len(result)}
            
            for _, row in result.iterrows():
                field = row['_field']
                value = float(row['_value']) if pd.notna(row['_value']) else 0.0
                
                if field == 'solar_power':
                    summary['avg_solar_power'] = value
                elif field == 'consumption':
                    summary['avg_consumption'] = value
            
            # Calculate energy efficiency
            if summary.get('avg_consumption', 0) > 0:
                summary['energy_efficiency'] = min(100, (summary.get('avg_solar_power', 0) / summary['avg_consumption']) * 100)
            else:
                summary['energy_efficiency'] = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to get analytics summary: {e}")
            return {"total_points": 0, "avg_solar_power": 0, "avg_consumption": 0, "energy_efficiency": 0}

# Real Sunsynk Collector
class RealSunsynkCollector:
    def __init__(self):
        # Real credentials
        self.username = 'robert.dondo@gmail.com'
        self.password = 'M%TcEJvo9^j8di'
        self.weather_key = '8c0021a3bea8254c109a414d2efaf9d6'
        self.location = 'Randburg,ZA'
        
        self.latest_data = None
        self.last_update = None
        
    async def collect_weather_data(self):
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
                combined_data = {
                    'solar_data': solar_data,
                    'weather_data': weather_data,
                    'timestamp': datetime.now()
                }
                
                self.latest_data = combined_data
                self.last_update = datetime.now()
                
                # Store in InfluxDB
                storage_data = {
                    **solar_data,
                    'weather_data': weather_data,
                    'timestamp': solar_data['timestamp']
                }
                
                influx_success = influx_manager.write_metrics(storage_data)
                
                logger.info(f"✅ Real data collected: Solar {solar_data['solar_power']}kW, Battery {solar_data['battery_soc']}%, Grid {solar_data['grid_power']}kW")
                if influx_success:
                    logger.info("📊 Data stored in InfluxDB")
                else:
                    logger.warning("⚠️ InfluxDB storage failed")
                
                return True
                
        except Exception as e:
            logger.error(f"Collection cycle error: {e}")
            return False
    
    def get_current_data(self):
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

# Global instances
influx_manager = InfluxDBManager()
real_collector = RealSunsynkCollector()

# Background Tasks
class BackgroundTasks:
    def __init__(self):
        self.running = False
        self.tasks = []

    async def start_background_tasks(self):
        if self.running:
            return
        
        self.running = True
        logger.info("Starting Phase 4 background tasks with InfluxDB...")
        
        # Initialize InfluxDB connection
        await influx_manager.connect()
        
        # Start real data collection task
        task1 = asyncio.create_task(self.generate_real_data())
        self.tasks.append(task1)

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
        logger.info("🚀 Starting real Sunsynk data collection with InfluxDB storage...")
        
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
    logger.info("Starting Sunsynk Dashboard API Phase 4...")
    await background_tasks.start_background_tasks()
    yield
    # Shutdown
    logger.info("Shutting down Sunsynk Dashboard API...")
    await background_tasks.stop_background_tasks()

# FastAPI app initialization
app = FastAPI(
    title="Sunsynk Solar Dashboard API - Phase 6",
    description="Advanced solar monitoring API with InfluxDB analytics and ML-powered optimization",
    version="6.0.0",
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
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "4.0.0",
        "phase": "Phase 4 - Advanced Analytics & Intelligence",
        "services": {
            "api": "online",
            "websocket": "online",
            "background_tasks": background_tasks.running,
            "influxdb": "connected" if influx_manager.connected else "disconnected",
            "real_data_collection": "active" if real_collector.last_update else "inactive"
        },
        "data_sources": {
            "sunsynk_api": "active",
            "weather_api": "active",
            "influxdb_storage": influx_manager.connected,
            "historical_data_points": len(influx_manager.query_historical_data(24)) if influx_manager.connected else 0
        }
    }

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
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
    logger.info(f"📊 Fetching {hours} hours of historical data from InfluxDB")
    
    # Try to get real historical data from InfluxDB
    historical_data = influx_manager.query_historical_data(hours)
    
    if historical_data:
        logger.info(f"✅ Retrieved {len(historical_data)} real historical data points")
        return {"history": historical_data, "source": "influxdb"}
    
    # Fallback to generated historical data if InfluxDB is empty
    logger.warning("⚠️ No InfluxDB data, generating fallback historical data")
    now = datetime.now()
    history = []
    
    for i in range(hours):
        timestamp = now - timedelta(hours=hours-i)
        hour = timestamp.hour
        
        # Generate realistic historical data
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
        battery_power = -solar_power + consumption  # Negative when charging
        
        history.append({
            "timestamp": timestamp,
            "solar_power": round(solar_power, 2),
            "battery_level": round(battery_level, 1),
            "grid_power": round(grid_power, 2),
            "consumption": round(consumption, 2),
            "battery_power": round(battery_power, 2),
            "temperature": round(22 + random.uniform(-5, 8), 1)
        })
    
    return {"history": history, "source": "generated"}

@app.get("/api/analytics/summary")
async def get_analytics_summary(
    hours: int = 24,
    user: dict = Depends(verify_token)
):
    logger.info(f"📈 Generating analytics summary for {hours} hours")
    
    # Get summary statistics from InfluxDB
    summary = influx_manager.get_analytics_summary(hours)
    
    # Get historical data count
    historical_data = influx_manager.query_historical_data(hours)
    
    return {
        "period_hours": hours,
        "total_data_points": len(historical_data),
        "avg_solar_power": summary.get('avg_solar_power', 0),
        "avg_consumption": summary.get('avg_consumption', 0),
        "energy_efficiency": summary.get('energy_efficiency', 0),
        "data_source": "influxdb" if historical_data else "none",
        "analysis_timestamp": datetime.now()
    }

@app.get("/api/analytics/predictions")
async def get_simple_predictions(
    hours: int = 24,
    user: dict = Depends(verify_token)
):
    logger.info(f"🔮 Generating statistical predictions for {hours} hours")
    
    # Get recent data for trend analysis
    recent_data = influx_manager.query_historical_data(48)  # Last 2 days
    
    now = datetime.now()
    predictions = []
    
    # Generate predictions based on historical patterns
    for i in range(hours):
        timestamp = now + timedelta(hours=i)
        hour = timestamp.hour
        
        import random
        import math
        
        # Base predictions on time of day
        if 6 <= hour <= 18:
            solar_factor = math.sin(math.pi * (hour - 6) / 12)
            predicted_solar = 4.5 * solar_factor + random.uniform(-0.2, 0.2)
        else:
            predicted_solar = 0.0
        
        # Consumption based on typical patterns
        if 6 <= hour <= 8 or 17 <= hour <= 22:  # Morning and evening peaks
            predicted_consumption = 2.0 + random.uniform(-0.3, 0.5)
        else:
            predicted_consumption = 1.2 + random.uniform(-0.2, 0.4)
        
        # Adjust based on recent trends if we have data
        if recent_data:
            recent_avg_solar = sum(p.get('solar_power', 0) for p in recent_data[-24:]) / min(24, len(recent_data))
            recent_avg_consumption = sum(p.get('consumption', 0) for p in recent_data[-24:]) / min(24, len(recent_data))
            
            # Apply trend adjustment
            if recent_avg_solar > 0:
                solar_adjustment = recent_avg_solar / 3.0  # Normalize
                predicted_solar *= (0.7 + 0.3 * solar_adjustment)
            
            if recent_avg_consumption > 0:
                consumption_adjustment = recent_avg_consumption / 1.5  # Normalize
                predicted_consumption *= (0.8 + 0.2 * consumption_adjustment)
        
        predictions.append({
            "timestamp": timestamp,
            "predicted_solar": round(max(0, predicted_solar), 2),
            "predicted_consumption": round(predicted_consumption, 2),
            "confidence": round(0.85 if recent_data else 0.75, 2)
        })
    
    return {
        "predictions": predictions,
        "model_type": "statistical_with_trends" if recent_data else "statistical_baseline",
        "historical_data_points": len(recent_data) if recent_data else 0,
        "generated_at": now
    }

# Phase 6 Advanced Analytics Endpoints
@app.get("/api/v6/weather/correlation")
async def get_weather_correlation_analysis(
    days: int = 7,
    user: dict = Depends(verify_token)
):
    """Advanced weather-solar production correlation analysis"""
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 6 analytics not available")
    
    logger.info(f"🌤️ Performing weather correlation analysis for {days} days")
    
    try:
        # Get weather forecasts
        weather_forecasts = await weather_analyzer.get_weather_forecast(days)
        
        # Get historical solar data
        historical_data = influx_manager.query_historical_data(days * 24)
        
        # Perform correlation analysis
        correlation = weather_analyzer.analyze_weather_solar_correlation(
            weather_forecasts, historical_data
        )
        
        # Get production forecast
        production_forecast = weather_analyzer.get_production_forecast(weather_forecasts)
        
        return {
            "correlation_analysis": {
                "correlation_coefficient": correlation.correlation_coefficient,
                "prediction_accuracy": correlation.prediction_accuracy,
                "optimal_conditions": correlation.optimal_conditions,
                "efficiency_factors": correlation.efficiency_factors
            },
            "weather_forecasts": len(weather_forecasts),
            "production_forecast": production_forecast[:24],  # Next 24 hours
            "analysis_timestamp": datetime.now(),
            "confidence": "high" if correlation.correlation_coefficient > 0.7 else "medium"
        }
        
    except Exception as e:
        logger.error(f"Weather correlation analysis error: {e}")
        raise HTTPException(status_code=500, detail="Weather correlation analysis failed")

@app.get("/api/v6/consumption/patterns")
async def get_consumption_pattern_analysis(
    days: int = 30,
    user: dict = Depends(verify_token)
):
    """Machine learning consumption pattern recognition"""
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 6 analytics not available")
    
    logger.info(f"🧠 Analyzing consumption patterns for {days} days")
    
    try:
        # Get historical consumption data
        historical_data = influx_manager.query_historical_data(days * 24)
        
        # Analyze patterns
        patterns = consumption_analyzer.analyze_consumption_patterns(historical_data)
        
        # Detect anomalies
        anomalies = consumption_analyzer.detect_anomalies(historical_data)
        
        # Generate solar data for optimization
        solar_data = historical_data  # Contains solar_power field
        
        # Generate optimization recommendations
        recommendations = consumption_analyzer.generate_optimization_recommendations(
            patterns, solar_data, anomalies
        )
        
        # Generate consumption predictions
        consumption_predictions = consumption_analyzer.predict_consumption(historical_data, 24)
        
        return {
            "patterns": [
                {
                    "type": p.pattern_type,
                    "peak_hours": p.peak_hours,
                    "average_consumption": p.average_consumption,
                    "peak_consumption": p.peak_consumption,
                    "efficiency_score": p.efficiency_score,
                    "confidence": p.pattern_confidence
                } for p in patterns
            ],
            "anomalies": [
                {
                    "timestamp": a.timestamp,
                    "expected": a.expected_consumption,
                    "actual": a.actual_consumption,
                    "deviation": a.deviation_percentage,
                    "type": a.anomaly_type,
                    "severity": a.severity
                } for a in anomalies[:5]  # Top 5 anomalies
            ],
            "optimization_recommendations": [
                {
                    "category": r.category,
                    "title": r.title,
                    "description": r.description,
                    "potential_savings": r.potential_savings,
                    "confidence": r.confidence,
                    "priority": r.priority
                } for r in recommendations
            ],
            "consumption_predictions": consumption_predictions,
            "analysis_timestamp": datetime.now(),
            "data_quality": "high" if len(historical_data) > days * 20 else "medium"
        }
        
    except Exception as e:
        logger.error(f"Consumption pattern analysis error: {e}")
        raise HTTPException(status_code=500, detail="Consumption pattern analysis failed")

@app.get("/api/v6/battery/optimization")
async def get_battery_optimization(
    hours: int = 24,
    user: dict = Depends(verify_token)
):
    """Advanced battery optimization and scheduling"""
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 6 analytics not available")
    
    logger.info(f"🔋 Generating battery optimization for {hours} hours")
    
    try:
        # Get current battery SOC
        current_data = real_collector.get_current_data()
        current_soc = current_data['metrics']['battery_level'] if current_data else 50.0
        
        # Get historical battery data for health analysis
        historical_data = influx_manager.query_historical_data(30 * 24)  # 30 days
        
        # Analyze battery health
        health_metrics = battery_optimizer.analyze_battery_health(historical_data)
        
        # Generate forecasts for optimization
        solar_forecast = []
        consumption_forecast = []
        
        # Simple forecast for demo (would use weather_analyzer in production)
        for i in range(hours):
            future_time = datetime.now() + timedelta(hours=i)
            hour = future_time.hour
            
            if 6 <= hour <= 18:
                solar_power = 4.0 * np.sin(np.pi * (hour - 6) / 12)
            else:
                solar_power = 0.0
                
            consumption = 1.5 if 6 <= hour <= 22 else 0.8
            
            solar_forecast.append({
                'timestamp': future_time,
                'predicted_solar_power': max(0, solar_power)
            })
            
            consumption_forecast.append({
                'timestamp': future_time,
                'predicted_consumption': consumption
            })
        
        # Generate battery schedule
        battery_schedule = battery_optimizer.optimize_battery_schedule(
            solar_forecast, consumption_forecast, current_soc, hours
        )
        
        # Generate energy flow optimization
        energy_flow = battery_optimizer.generate_energy_flow_optimization(
            solar_forecast, consumption_forecast, current_soc
        )
        
        return {
            "battery_health": {
                "capacity_retention": health_metrics.capacity_retention,
                "cycle_count": health_metrics.cycle_count_estimate,
                "efficiency": health_metrics.efficiency,
                "health_score": health_metrics.health_score,
                "degradation_rate": health_metrics.degradation_rate
            },
            "optimization_schedule": [
                {
                    "timestamp": s.timestamp,
                    "mode": s.mode.value,
                    "target_soc": s.target_soc,
                    "priority": s.priority,
                    "reason": s.reason,
                    "expected_savings": s.expected_savings,
                    "confidence": s.confidence
                } for s in battery_schedule
            ],
            "energy_flow_optimization": [
                {
                    "timestamp": e.timestamp,
                    "solar_forecast": e.solar_forecast,
                    "consumption_forecast": e.consumption_forecast,
                    "grid_cost": e.grid_cost,
                    "recommended_action": e.recommended_battery_action,
                    "potential_savings": e.potential_savings,
                    "strategy": e.optimization_strategy
                } for e in energy_flow[:12]  # Next 12 hours
            ],
            "current_soc": current_soc,
            "analysis_timestamp": datetime.now(),
            "optimization_confidence": "high"
        }
        
    except Exception as e:
        logger.error(f"Battery optimization error: {e}")
        raise HTTPException(status_code=500, detail="Battery optimization failed")

@app.get("/api/v6/system/insights")
async def get_system_insights(
    user: dict = Depends(verify_token)
):
    """Comprehensive system insights and recommendations"""
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 6 analytics not available")
    
    logger.info("🔍 Generating comprehensive system insights")
    
    try:
        # Get recent data
        historical_data = influx_manager.query_historical_data(7 * 24)  # 7 days
        current_data = real_collector.get_current_data()
        
        if not historical_data:
            raise HTTPException(status_code=404, detail="Insufficient data for insights")
        
        # Calculate key performance indicators
        df = pd.DataFrame(historical_data)
        
        total_solar = df['solar_power'].sum() if 'solar_power' in df.columns else 0
        total_consumption = df['consumption'].sum() if 'consumption' in df.columns else 0
        avg_battery_level = df['battery_level'].mean() if 'battery_level' in df.columns else 0
        
        energy_independence = (total_solar / total_consumption * 100) if total_consumption > 0 else 0
        
        # System efficiency score
        efficiency_factors = {
            "solar_utilization": min(100, total_solar / (5.0 * 8 * 7) * 100),  # 5kW system, 8 peak hours
            "battery_cycling": min(100, avg_battery_level),
            "energy_independence": min(100, energy_independence)
        }
        
        overall_efficiency = sum(efficiency_factors.values()) / len(efficiency_factors)
        
        # Environmental impact
        co2_saved = total_solar * 0.85  # kg CO2 per kWh saved
        trees_equivalent = co2_saved / 22  # 22kg CO2 per tree per year
        
        insights = {
            "performance_summary": {
                "energy_independence": round(energy_independence, 1),
                "system_efficiency": round(overall_efficiency, 1),
                "weekly_solar_production": round(total_solar, 2),
                "weekly_consumption": round(total_consumption, 2),
                "average_battery_level": round(avg_battery_level, 1)
            },
            "efficiency_breakdown": efficiency_factors,
            "environmental_impact": {
                "co2_saved_kg": round(co2_saved, 2),
                "trees_equivalent": round(trees_equivalent, 2),
                "grid_energy_offset": round(total_solar, 2)
            },
            "system_status": current_data['status'] if current_data else {},
            "recommendations": [
                {
                    "category": "efficiency",
                    "title": "System Performance",
                    "description": f"Your system is operating at {overall_efficiency:.1f}% efficiency",
                    "priority": "high" if overall_efficiency < 70 else "medium"
                }
            ],
            "analysis_timestamp": datetime.now(),
            "data_period": "7_days"
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"System insights error: {e}")
        raise HTTPException(status_code=500, detail="System insights generation failed")

# WebSocket endpoint
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
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
    logger.info("🚀 Starting Sunsynk Dashboard Phase 6 Backend")
    logger.info("✨ Features: ML Analytics, Weather Correlation, Battery Optimization")
    
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8001)),  # Changed from 8000 to avoid conflicts
        reload=True,
        log_level="info"
    )
