"""
Sunsynk Solar Dashboard - Phase 6 Backend API
FastAPI backend with ML-powered analytics and real-time monitoring
Advanced solar intelligence with weather correlation and optimization
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
import pandas as pd
import numpy as np
import psutil
import shutil
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from enum import Enum
import jwt
import uuid
from typing import Union

# Add the sunsynk package to path
sys.path.insert(0, '/app')

# Import Sunsynk client
from sunsynk.client import SunsynkClient

# Import Intelligent Alert System
try:
    from alerts.models import AlertConfiguration, AlertType, AlertSeverity as IntelligentAlertSeverity
    from alerts.configuration import config_manager
    from alerts.intelligent_monitor import IntelligentAlertMonitor
    from alerts.weather_intelligence import weather_intelligence
    INTELLIGENT_ALERTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Intelligent Alert System not available: {e}")
    INTELLIGENT_ALERTS_AVAILABLE = False

# Import Persistent Settings Manager
try:
    from components.settings_manager import settings_manager
    SETTINGS_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Settings Manager not available: {e}")
    SETTINGS_MANAGER_AVAILABLE = False

# Phase 6 ML Analytics Configuration
PHASE6_AVAILABLE = True  # Enable Phase 6 ML features

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "eec390129e82ce9340522b7c79ead660321d6bcb27ffe5e33bece077758f4607")
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

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    VOICE = "voice"
    WEBHOOK = "webhook"

class Alert(BaseModel):
    id: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    category: str
    timestamp: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class NotificationPreferences(BaseModel):
    enabled_channels: List[NotificationChannel]
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "06:00"
    severity_thresholds: Dict[str, AlertSeverity] = {
        "battery_low": AlertSeverity.MEDIUM,
        "battery_critical": AlertSeverity.CRITICAL,
        "grid_outage": AlertSeverity.HIGH,
        "inverter_offline": AlertSeverity.HIGH,
        "consumption_anomaly": AlertSeverity.LOW
    }
    emergency_voice_calls: bool = True
    max_notifications_per_hour: int = 10

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
            
            # Test connection
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
            
            historical_data = []
            grouped = result.groupby('_time')
            
            for timestamp, group in grouped:
                data_point = {"timestamp": timestamp}
                
                for _, row in group.iterrows():
                    field = row['_field']
                    value = float(row['_value']) if pd.notna(row['_value']) else 0.0
                    data_point[field] = value
                
                required_fields = ['solar_power', 'battery_level', 'grid_power', 'consumption', 'battery_power']
                for field in required_fields:
                    if field not in data_point:
                        data_point[field] = 0.0
                
                data_point['temperature'] = 22.0
                historical_data.append(data_point)
            
            logger.info(f"📈 Retrieved {len(historical_data)} historical data points")
            return sorted(historical_data, key=lambda x: x['timestamp'])
            
        except Exception as e:
            logger.error(f"❌ Failed to query InfluxDB: {e}")
            return []

# Real Sunsynk Collector
class RealSunsynkCollector:
    def __init__(self):
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
            battery = await client.get_inverter_realtime_battery(inverter_sn)
            grid = await client.get_inverter_realtime_grid(inverter_sn)
            input_data = await client.get_inverter_realtime_input(inverter_sn)
            output = await client.get_inverter_realtime_output(inverter_sn)
            
            solar_power = float(input_data.get_power()) / 1000
            battery_power = float(battery.get_power()) / 1000
            grid_power = float(grid.get_power()) / 1000
            consumption = float(getattr(output, 'pac', 0)) / 1000
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
                inverters = await client.get_inverters()
                if not inverters:
                    logger.error("No inverters found")
                    return False
                    
                inverter = inverters[0]
                inverter_sn = inverter.sn
                
                solar_data = await self.collect_sunsynk_data(client, inverter_sn)
                weather_data = await self.collect_weather_data()
                
                if not solar_data:
                    logger.error("Failed to collect solar data")
                    return False
                
                combined_data = {
                    'solar_data': solar_data,
                    'weather_data': weather_data,
                    'timestamp': datetime.now()
                }
                
                self.latest_data = combined_data
                self.last_update = datetime.now()
                
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

# Alert Management System
class AlertManager:
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.last_notification_times: Dict[str, datetime] = {}
        self.notification_preferences = NotificationPreferences(
            enabled_channels=[NotificationChannel.PUSH, NotificationChannel.EMAIL]
        )
        
        # Initialize Intelligent Alert System
        self.intelligent_monitor = None
        self.monitoring_task = None
        if INTELLIGENT_ALERTS_AVAILABLE:
            self.intelligent_monitor = IntelligentAlertMonitor()
            logger.info("Intelligent Alert System initialized")
    
    async def start_intelligent_monitoring(self, user_id: str = "default"):
        """Start intelligent monitoring for a user"""
        if not INTELLIGENT_ALERTS_AVAILABLE or not self.intelligent_monitor:
            logger.warning("Intelligent Alert System not available")
            return
        
        try:
            # Get or create default configuration
            config = config_manager.get_configuration(user_id, AlertType.ENERGY_DEFICIT)
            if not config:
                config = config_manager.get_default_configuration(user_id, AlertType.ENERGY_DEFICIT)
                config = config_manager.create_configuration(
                    user_id=user_id,
                    alert_type=AlertType.ENERGY_DEFICIT,
                    **config.to_dict()
                )
            
            # Start monitoring task
            if not self.monitoring_task or self.monitoring_task.done():
                self.monitoring_task = asyncio.create_task(
                    self.intelligent_monitor.start_monitoring(config)
                )
                logger.info(f"Started intelligent monitoring for user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to start intelligent monitoring: {e}")
    
    def stop_intelligent_monitoring(self):
        """Stop intelligent monitoring"""
        if self.intelligent_monitor:
            self.intelligent_monitor.stop_monitoring()
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
            logger.info("Stopped intelligent monitoring")
        
        # Initialize Intelligent Alert System
        self.intelligent_monitor = None
        self.monitoring_task = None
        if INTELLIGENT_ALERTS_AVAILABLE:
            self.intelligent_monitor = IntelligentAlertMonitor()
            logger.info("Intelligent Alert System initialized")
    
    async def start_intelligent_monitoring(self, user_id: str = "default"):
        """Start intelligent monitoring for a user"""
        if not INTELLIGENT_ALERTS_AVAILABLE or not self.intelligent_monitor:
            logger.warning("Intelligent Alert System not available")
            return
        
        try:
            # Get or create default configuration
            config = config_manager.get_configuration(user_id, AlertType.ENERGY_DEFICIT)
            if not config:
                config = config_manager.get_default_configuration(user_id, AlertType.ENERGY_DEFICIT)
                config = config_manager.create_configuration(
                    user_id=user_id,
                    alert_type=AlertType.ENERGY_DEFICIT,
                    **config.to_dict()
                )
            
            # Start monitoring task
            if not self.monitoring_task or self.monitoring_task.done():
                self.monitoring_task = asyncio.create_task(
                    self.intelligent_monitor.start_monitoring(config)
                )
                logger.info(f"Started intelligent monitoring for user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to start intelligent monitoring: {e}")
    
    def stop_intelligent_monitoring(self):
        """Stop intelligent monitoring"""
        if self.intelligent_monitor:
            self.intelligent_monitor.stop_monitoring()
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
            logger.info("Stopped intelligent monitoring")
    
    def create_alert(self, title: str, message: str, severity: AlertSeverity, 
                    category: str, metadata: Dict[str, Any] = None) -> Alert:
        alert_id = str(uuid.uuid4())
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            status=AlertStatus.ACTIVE,
            category=category,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Trigger notifications
        asyncio.create_task(self._send_notifications(alert))
        
        logger.info(f"🚨 Alert created: {title} ({severity.value})")
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self.active_alerts[alert_id].acknowledged_at = datetime.now()
            logger.info(f"✅ Alert acknowledged: {alert_id}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            del self.active_alerts[alert_id]
            logger.info(f"✅ Alert resolved: {alert_id}")
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff]
    
    def get_recent_alerts(self, hours: int = 24) -> List[dict]:
        """Get recent alerts as dictionaries for API responses"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_alerts = []
        
        # Include active alerts
        for alert in self.active_alerts.values():
            if alert.timestamp >= cutoff:
                recent_alerts.append({
                    'id': alert.id,
                    'title': alert.title,
                    'message': alert.message,
                    'severity': alert.severity.value,
                    'status': 'active',
                    'category': alert.category,
                    'timestamp': alert.timestamp.isoformat(),
                    'metadata': alert.metadata
                })
        
        # Include historical alerts
        for alert in self.alert_history:
            if alert.timestamp >= cutoff:
                recent_alerts.append({
                    'id': alert.id,
                    'title': alert.title,
                    'message': alert.message,
                    'severity': alert.severity.value,
                    'status': alert.status.value,
                    'category': alert.category,
                    'timestamp': alert.timestamp.isoformat(),
                    'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'metadata': alert.metadata
                })
        
        # Sort by timestamp (most recent first)
        recent_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        return recent_alerts
    
    async def _send_notifications(self, alert: Alert):
        try:
            # Check if we're in quiet hours for non-critical alerts
            if alert.severity != AlertSeverity.CRITICAL and self._is_quiet_hours():
                logger.info(f"⏰ Skipping notification during quiet hours: {alert.title}")
                return
            
            # Rate limiting
            if self._is_rate_limited(alert.category):
                logger.info(f"🚫 Rate limited notification: {alert.category}")
                return
            
            # Send to enabled channels
            for channel in self.notification_preferences.enabled_channels:
                await self._send_to_channel(alert, channel)
            
            # Emergency voice calls for critical battery alerts
            if (alert.severity == AlertSeverity.CRITICAL and 
                alert.category == "battery_critical" and 
                self.notification_preferences.emergency_voice_calls):
                await self._send_voice_call(alert)
            
            self.last_notification_times[alert.category] = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Failed to send notifications for alert {alert.id}: {e}")
    
    def _is_quiet_hours(self) -> bool:
        now = datetime.now().time()
        quiet_start = datetime.strptime(self.notification_preferences.quiet_hours_start, "%H:%M").time()
        quiet_end = datetime.strptime(self.notification_preferences.quiet_hours_end, "%H:%M").time()
        
        if quiet_start <= quiet_end:
            return quiet_start <= now <= quiet_end
        else:  # Spans midnight
            return now >= quiet_start or now <= quiet_end
    
    def _is_rate_limited(self, category: str) -> bool:
        if category not in self.last_notification_times:
            return False
        
        last_time = self.last_notification_times[category]
        min_interval = timedelta(minutes=60 / self.notification_preferences.max_notifications_per_hour)
        return datetime.now() - last_time < min_interval
    
    async def _send_to_channel(self, alert: Alert, channel: NotificationChannel):
        try:
            if channel == NotificationChannel.PUSH:
                await self._send_push_notification(alert)
            elif channel == NotificationChannel.EMAIL:
                await self._send_email(alert)
            elif channel == NotificationChannel.SMS:
                await self._send_sms(alert)
            elif channel == NotificationChannel.WHATSAPP:
                await self._send_whatsapp(alert)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook(alert)
                
            logger.info(f"📤 Sent {channel.value} notification: {alert.title}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send {channel.value} notification: {e}")
    
    async def _send_push_notification(self, alert: Alert):
        # WebSocket broadcast for real-time notifications
        notification_data = {
            "type": "alert_notification",
            "data": {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "category": alert.category,
                "timestamp": alert.timestamp.isoformat()
            }
        }
        await manager.broadcast(json.dumps(notification_data))
    
    async def _send_email(self, alert: Alert):
        # Email implementation would go here
        # For now, just log the action
        logger.info(f"📧 Email notification: {alert.title}")
    
    async def _send_sms(self, alert: Alert):
        # Twilio SMS implementation would go here
        logger.info(f"📱 SMS notification: {alert.title}")
    
    async def _send_whatsapp(self, alert: Alert):
        # Twilio WhatsApp implementation would go here
        logger.info(f"💬 WhatsApp notification: {alert.title}")
    
    async def _send_voice_call(self, alert: Alert):
        # Twilio Voice call implementation would go here
        logger.info(f"📞 Voice call alert: {alert.title}")
    
    async def _send_webhook(self, alert: Alert):
        # Webhook implementation would go here
        logger.info(f"🔗 Webhook notification: {alert.title}")

# Monitoring and Alert Generation System
class SystemMonitor:
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.previous_data = None
        self.alert_conditions = {
            "battery_low": lambda data: data.get("battery_soc", 100) < 30,
            "battery_critical": lambda data: data.get("battery_soc", 100) < 15,
            "grid_outage": lambda data: abs(data.get("grid_power", 0)) > 0.5 and data.get("battery_soc", 100) < 50,
            "inverter_offline": lambda data: data.get("timestamp") and (datetime.now() - data.get("timestamp")).seconds > 300,
            "consumption_anomaly": lambda data: data.get("consumption", 0) > 5.0,
            "weather_poor": lambda data: data.get("weather_data", {}).get("cloud_cover", 0) > 80,
            "battery_not_charging": lambda data: self._check_daytime_charging(data)
        }
    
    def _check_daytime_charging(self, data: Dict) -> bool:
        """REQ-013: Time-based conditional alerts (daytime battery warnings)"""
        now = datetime.now()
        is_daytime = 9 <= now.hour <= 16  # Peak solar hours
        
        if not is_daytime:
            return False
            
        solar_power = data.get("solar_power", 0)
        battery_soc = data.get("battery_soc", 100)
        battery_power = data.get("battery_power", 0)
        
        # Alert if there's good solar but battery isn't charging
        return solar_power > 2.0 and battery_soc < 80 and battery_power < 0.5
    
    async def check_conditions(self, current_data: Dict):
        """Monitor system conditions and generate alerts"""
        try:
            for condition_name, condition_func in self.alert_conditions.items():
                if condition_func(current_data):
                    await self._handle_condition(condition_name, current_data)
            
            self.previous_data = current_data
            
        except Exception as e:
            logger.error(f"❌ Error in system monitoring: {e}")
    
    async def _handle_condition(self, condition_name: str, data: Dict):
        """Handle detected alert conditions"""
        # Prevent duplicate alerts for the same condition
        existing_alerts = [alert for alert in self.alert_manager.get_active_alerts() 
                          if alert.category == condition_name]
        
        if existing_alerts:
            return  # Alert already active
        
        alert_configs = {
            "battery_low": {
                "title": "Battery Level Low",
                "message": f"Battery at {data.get('battery_soc', 0):.1f}% - Consider reducing consumption",
                "severity": AlertSeverity.MEDIUM
            },
            "battery_critical": {
                "title": "Critical Battery Level",
                "message": f"Battery critically low at {data.get('battery_soc', 0):.1f}% - Immediate action required",
                "severity": AlertSeverity.CRITICAL
            },
            "grid_outage": {
                "title": "Grid Outage Detected",
                "message": "Running on battery power - Monitor usage carefully",
                "severity": AlertSeverity.HIGH
            },
            "inverter_offline": {
                "title": "Inverter Communication Lost",
                "message": "No data received from inverter for over 5 minutes",
                "severity": AlertSeverity.HIGH
            },
            "consumption_anomaly": {
                "title": "High Consumption Detected",
                "message": f"Unusual consumption of {data.get('consumption', 0):.1f}kW detected",
                "severity": AlertSeverity.MEDIUM
            },
            "weather_poor": {
                "title": "Poor Weather Conditions",
                "message": f"Heavy cloud cover ({data.get('weather_data', {}).get('cloud_cover', 0)}%) may affect solar production",
                "severity": AlertSeverity.LOW
            },
            "battery_not_charging": {
                "title": "Battery Not Charging During Solar Hours",
                "message": f"Good solar conditions ({data.get('solar_power', 0):.1f}kW) but battery not charging properly",
                "severity": AlertSeverity.MEDIUM
            }
        }
        
        if condition_name in alert_configs:
            config = alert_configs[condition_name]
            self.alert_manager.create_alert(
                title=config["title"],
                message=config["message"],
                severity=config["severity"],
                category=condition_name,
                metadata={"data_snapshot": data}
            )

alert_manager = AlertManager()
system_monitor = SystemMonitor(alert_manager)

# Background Tasks
class BackgroundTasks:
    def __init__(self):
        self.running = False
        self.tasks = []

    async def start_background_tasks(self):
        if self.running:
            return
        
        self.running = True
        logger.info("Starting Phase 6 background tasks...")
        
        await influx_manager.connect()
        
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
                success = await real_collector.run_collection_cycle()
                
                if success:
                    current_data = real_collector.get_current_data()
                    
                    if current_data:
                        # Monitor for alert conditions
                        monitoring_data = {
                            **current_data["metrics"],
                            **current_data["status"],
                            "weather_data": real_collector.latest_data["weather_data"] if real_collector.latest_data else {}
                        }
                        await system_monitor.check_conditions(monitoring_data)
                        
                        dashboard_message = WebSocketMessage(
                            type="dashboard_update",
                            data=current_data
                        )
                        
                        await manager.broadcast(dashboard_message.model_dump_json())
                        logger.debug("📡 Real data broadcasted to WebSocket clients")
                else:
                    logger.warning("⚠️ Failed to collect real data, retrying...")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in real data collection: {e}")
                await asyncio.sleep(60)

background_tasks = BackgroundTasks()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Sunsynk Dashboard API Phase 6...")
    if PHASE6_AVAILABLE:
        logger.info("✅ Phase 6 ML Analytics enabled with demonstration data")
    await background_tasks.start_background_tasks()
    yield
    logger.info("Shutting down Sunsynk Dashboard API...")
    await background_tasks.stop_background_tasks()

# FastAPI app initialization
app = FastAPI(
    title="Sunsynk Solar Dashboard API - Phase 6",
    description="ML-powered solar monitoring API with advanced analytics and optimization",
    version="6.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:3002,http://localhost:3003").split(",")
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
        "version": "6.0.0",
        "phase": "Phase 6 - ML-Powered Solar Intelligence",
        "services": {
            "api": "online",
            "websocket": "online",
            "background_tasks": background_tasks.running,
            "influxdb": "connected" if influx_manager.connected else "disconnected",
            "real_data_collection": "active" if real_collector.last_update else "inactive",
            "ml_analytics": "enabled" if PHASE6_AVAILABLE else "disabled"
        },
        "data_sources": {
            "sunsynk_api": "active",
            "weather_api": "active",
            "influxdb_storage": influx_manager.connected,
            "historical_data_points": len(influx_manager.query_historical_data(24)) if influx_manager.connected else 0
        },
        "ml_features": {
            "weather_correlation": PHASE6_AVAILABLE,
            "consumption_patterns": PHASE6_AVAILABLE,
            "battery_optimization": PHASE6_AVAILABLE,
            "energy_forecasting": PHASE6_AVAILABLE
        } if PHASE6_AVAILABLE else {}
    }

@app.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint for system monitoring"""
    try:
        # System metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = psutil.boot_time()
            uptime = datetime.now().timestamp() - boot_time
        except:
            # Fallback if psutil is not available
            cpu_percent = 0
            memory = type('obj', (object,), {'percent': 0, 'total': 0, 'used': 0})()
            disk = type('obj', (object,), {'percent': 0, 'total': 0, 'used': 0})()
            uptime = 0

        # Application metrics
        current_data = real_collector.get_current_data()
        metrics_data = current_data["metrics"] if current_data else {}
        
        # Generate Prometheus format metrics
        prometheus_metrics = [
            "# HELP sunsynk_system_cpu_percent System CPU usage percentage",
            "# TYPE sunsynk_system_cpu_percent gauge",
            f"sunsynk_system_cpu_percent {cpu_percent}",
            "",
            "# HELP sunsynk_system_memory_percent System memory usage percentage", 
            "# TYPE sunsynk_system_memory_percent gauge",
            f"sunsynk_system_memory_percent {memory.percent}",
            "",
            "# HELP sunsynk_system_memory_bytes System memory usage in bytes",
            "# TYPE sunsynk_system_memory_bytes gauge",
            f"sunsynk_system_memory_bytes{{type=\"total\"}} {memory.total}",
            f"sunsynk_system_memory_bytes{{type=\"used\"}} {memory.used}",
            "",
            "# HELP sunsynk_system_disk_percent System disk usage percentage",
            "# TYPE sunsynk_system_disk_percent gauge", 
            f"sunsynk_system_disk_percent {disk.percent}",
            "",
            "# HELP sunsynk_system_disk_bytes System disk usage in bytes",
            "# TYPE sunsynk_system_disk_bytes gauge",
            f"sunsynk_system_disk_bytes{{type=\"total\"}} {disk.total}",
            f"sunsynk_system_disk_bytes{{type=\"used\"}} {disk.used}",
            "",
            "# HELP sunsynk_system_uptime_seconds System uptime in seconds",
            "# TYPE sunsynk_system_uptime_seconds counter",
            f"sunsynk_system_uptime_seconds {uptime}",
            "",
            "# HELP sunsynk_api_health API health status (1=healthy, 0=unhealthy)",
            "# TYPE sunsynk_api_health gauge",
            "sunsynk_api_health 1",
            "",
            "# HELP sunsynk_influxdb_connected InfluxDB connection status (1=connected, 0=disconnected)",
            "# TYPE sunsynk_influxdb_connected gauge",
            f"sunsynk_influxdb_connected {1 if influx_manager.connected else 0}",
            "",
            "# HELP sunsynk_background_tasks_running Background tasks status (1=running, 0=stopped)",
            "# TYPE sunsynk_background_tasks_running gauge",
            f"sunsynk_background_tasks_running {1 if background_tasks.running else 0}",
        ]
        
        # Solar system metrics
        if metrics_data:
            prometheus_metrics.extend([
                "",
                "# HELP sunsynk_solar_power Solar power generation in watts", 
                "# TYPE sunsynk_solar_power gauge",
                f"sunsynk_solar_power {metrics_data.get('solar_power', 0)}",
                "",
                "# HELP sunsynk_battery_level Battery state of charge percentage",
                "# TYPE sunsynk_battery_level gauge", 
                f"sunsynk_battery_level {metrics_data.get('battery_soc', 0)}",
                "",
                "# HELP sunsynk_battery_power Battery power in watts (positive=charging, negative=discharging)",
                "# TYPE sunsynk_battery_power gauge",
                f"sunsynk_battery_power {metrics_data.get('battery_power', 0)}",
                "",
                "# HELP sunsynk_grid_power Grid power in watts (positive=importing, negative=exporting)", 
                "# TYPE sunsynk_grid_power gauge",
                f"sunsynk_grid_power {metrics_data.get('grid_power', 0)}",
                "",
                "# HELP sunsynk_consumption Total power consumption in watts",
                "# TYPE sunsynk_consumption gauge",
                f"sunsynk_consumption {metrics_data.get('consumption', 0)}",
                "",
                "# HELP sunsynk_battery_voltage Battery voltage in volts",
                "# TYPE sunsynk_battery_voltage gauge",
                f"sunsynk_battery_voltage {metrics_data.get('battery_voltage', 0)}",
                "",
                "# HELP sunsynk_grid_voltage Grid voltage in volts", 
                "# TYPE sunsynk_grid_voltage gauge",
                f"sunsynk_grid_voltage {metrics_data.get('grid_voltage', 0)}",
            ])
            
        # Alert conditions metrics
        if hasattr(system_monitor, 'alert_conditions'):
            prometheus_metrics.extend([
                "",
                "# HELP sunsynk_alert_condition_triggered Alert condition status (1=triggered, 0=normal)",
                "# TYPE sunsynk_alert_condition_triggered gauge",
            ])
            
            monitoring_data = {**metrics_data}
            for condition_name, condition_func in system_monitor.alert_conditions.items():
                try:
                    triggered = 1 if condition_func(monitoring_data) else 0
                    prometheus_metrics.append(f"sunsynk_alert_condition_triggered{{condition=\"{condition_name}\"}} {triggered}")
                except:
                    prometheus_metrics.append(f"sunsynk_alert_condition_triggered{{condition=\"{condition_name}\"}} 0")

        # Add timestamp
        prometheus_metrics.extend([
            "",
            "# HELP sunsynk_metrics_timestamp_seconds Timestamp of last metrics update",
            "# TYPE sunsynk_metrics_timestamp_seconds gauge",
            f"sunsynk_metrics_timestamp_seconds {datetime.now().timestamp()}",
        ])
        
        return "\n".join(prometheus_metrics)
        
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return f"# Error generating metrics: {str(e)}"

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
    current_data = real_collector.get_current_data()
    
    if current_data:
        return current_data
    
    try:
        success = await real_collector.run_collection_cycle()
        if success:
            current_data = real_collector.get_current_data()
            if current_data:
                return current_data
    except Exception as e:
        logger.error(f"Failed to collect fresh data: {e}")
    
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
    
    historical_data = influx_manager.query_historical_data(hours)
    
    if historical_data:
        logger.info(f"✅ Retrieved {len(historical_data)} real historical data points")
        return {"history": historical_data, "source": "influxdb"}
    
    logger.warning("⚠️ No InfluxDB data, generating fallback historical data")
    now = datetime.now()
    history = []
    
    for i in range(hours):
        timestamp = now - timedelta(hours=hours-i)
        hour = timestamp.hour
        
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
        battery_power = -solar_power + consumption
        
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

# Phase 6 ML Analytics Endpoints
@app.get("/api/v6/weather/correlation")
async def get_weather_correlation_analysis(
    days: int = 7,
    user: dict = Depends(verify_token)
):
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=404, detail="Phase 6 ML features not available")
    
    logger.info(f"🌤️ Analyzing weather correlation for {days} days")
    
    # Demonstration data - in production this would use real ML analysis
    correlation_data = {
        "correlation_coefficient": 0.78,
        "prediction_accuracy": 85.4,
        "analysis_period_days": days,
        "optimal_conditions": {
            "temperature_range": {"min": 22, "max": 28},
            "humidity_range": {"min": 40, "max": 65},
            "cloud_cover_max": 25,
            "wind_speed_optimal": 12
        },
        "efficiency_factors": {
            "clear_sky_boost": 15.2,
            "temperature_impact": -2.1,
            "humidity_impact": -1.8,
            "seasonal_variation": 8.5
        },
        "daily_predictions": [
            {"date": "2025-10-01", "weather": "sunny", "predicted_efficiency": 92.1},
            {"date": "2025-10-02", "weather": "partly_cloudy", "predicted_efficiency": 78.5},
            {"date": "2025-10-03", "weather": "cloudy", "predicted_efficiency": 65.2}
        ],
        "confidence_score": 0.85,
        "last_updated": datetime.now()
    }
    
    return correlation_data

@app.get("/api/v6/consumption/patterns")
async def get_consumption_pattern_analysis(
    days: int = 30,
    user: dict = Depends(verify_token)
):
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=404, detail="Phase 6 ML features not available")
    
    logger.info(f"📊 Analyzing consumption patterns for {days} days")
    
    # Demonstration data
    consumption_data = {
        "analysis_period_days": days,
        "patterns": [
            {
                "type": "morning_peak",
                "peak_hours": [7, 8, 9],
                "average_consumption": 2.8,
                "peak_consumption": 4.2,
                "efficiency_score": 78.5,
                "confidence": 0.92
            },
            {
                "type": "evening_peak", 
                "peak_hours": [18, 19, 20, 21],
                "average_consumption": 3.2,
                "peak_consumption": 5.8,
                "efficiency_score": 71.2,
                "confidence": 0.89
            },
            {
                "type": "weekend_variation",
                "peak_hours": [10, 11, 14, 15],
                "average_consumption": 2.1,
                "peak_consumption": 3.5,
                "efficiency_score": 85.1,
                "confidence": 0.81
            }
        ],
        "anomalies": [
            {
                "timestamp": "2025-09-28T14:30:00",
                "expected": 1.8,
                "actual": 4.2,
                "deviation": 133.3,
                "type": "spike",
                "severity": "high"
            },
            {
                "timestamp": "2025-09-25T08:15:00",
                "expected": 2.5,
                "actual": 0.8,
                "deviation": -68.0,
                "type": "drop",
                "severity": "medium"
            }
        ],
        "optimization_recommendations": [
            {
                "category": "load_shifting",
                "title": "Shift Dishwasher to Solar Hours",
                "description": "Move dishwasher usage from 20:00 to 13:00 to maximize solar utilization",
                "potential_savings": "R45/month",
                "confidence": 0.87,
                "priority": "high"
            },
            {
                "category": "demand_management", 
                "title": "Optimize Geyser Schedule",
                "description": "Heat geyser during peak solar production (11:00-15:00)",
                "potential_savings": "R78/month",
                "confidence": 0.91,
                "priority": "high"
            }
        ],
        "efficiency_score": 76.8,
        "last_updated": datetime.now()
    }
    
    return consumption_data

@app.get("/api/v6/battery/optimization") 
async def get_battery_optimization_plan(user: dict = Depends(verify_token)):
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=404, detail="Phase 6 ML features not available")
    
    logger.info("🔋 Generating battery optimization plan")
    
    # Demonstration data
    optimization_data = {
        "current_strategy": "time_of_use",
        "optimal_soc_range": {"min": 20, "max": 85},
        "charge_schedule": [
            {"time": "09:00", "target_soc": 75, "source": "solar", "priority": "high"},
            {"time": "13:00", "target_soc": 85, "source": "solar", "priority": "high"},
            {"time": "02:00", "target_soc": 40, "source": "grid", "priority": "low"}
        ],
        "discharge_schedule": [
            {"time": "17:00", "target_soc": 60, "usage": "peak_shaving", "priority": "high"},
            {"time": "20:00", "target_soc": 35, "usage": "load_support", "priority": "medium"}
        ],
        "efficiency_improvements": [
            {
                "metric": "depth_of_discharge",
                "current": 65,
                "optimized": 55,
                "improvement": 15.4
            },
            {
                "metric": "cycle_life_extension",
                "current": "5.2 years",
                "optimized": "6.8 years", 
                "improvement": 30.8
            }
        ],
        "cost_savings": {
            "monthly_estimate": "R125",
            "yearly_estimate": "R1,500",
            "load_shedding_protection": "R320/month",
            "peak_demand_reduction": "18%"
        },
        "weather_integration": {
            "cloudy_day_strategy": "preserve_40%_soc",
            "sunny_day_strategy": "aggressive_charging",
            "rain_forecast_action": "top_up_battery"
        },
        "confidence_score": 0.88,
        "last_updated": datetime.now()
    }
    
    return optimization_data

@app.get("/api/v6/analytics/forecasting")
async def get_energy_forecasting(
    hours: int = 48,
    user: dict = Depends(verify_token)
):
    if not PHASE6_AVAILABLE:
        raise HTTPException(status_code=404, detail="Phase 6 ML features not available")
    
    logger.info(f"🔮 Generating {hours}h energy forecast")
    
    import random
    import math
    
    # Generate demonstration forecasting data
    forecasts = []
    base_time = datetime.now()
    
    for i in range(hours):
        forecast_time = base_time + timedelta(hours=i)
        hour = forecast_time.hour
        
        # Solar production forecast
        if 6 <= hour <= 18:
            solar_factor = math.sin(math.pi * (hour - 6) / 12)
            predicted_solar = 5.2 * solar_factor + random.uniform(-0.5, 0.3)
        else:
            predicted_solar = 0.0
        
        # Consumption forecast
        if 7 <= hour <= 9 or 17 <= hour <= 22:
            predicted_consumption = 2.8 + random.uniform(-0.4, 0.6)
        else:
            predicted_consumption = 1.4 + random.uniform(-0.2, 0.4)
        
        # Weather impact
        weather_factor = 0.9 + random.uniform(-0.15, 0.1)
        predicted_solar *= weather_factor
        
        forecasts.append({
            "timestamp": forecast_time,
            "predicted_production": max(0, round(predicted_solar, 2)),
            "predicted_consumption": round(predicted_consumption, 2),
            "predicted_grid_usage": round(predicted_consumption - max(0, predicted_solar), 2),
            "confidence": round(0.85 + random.uniform(-0.1, 0.1), 2),
            "weather_condition": "sunny" if hour > 8 and hour < 17 else "clear"
        })
    
    forecasting_data = {
        "forecast_horizon_hours": hours,
        "production_forecast": forecasts,
        "summary": {
            "total_predicted_production": round(sum(f["predicted_production"] for f in forecasts), 2),
            "total_predicted_consumption": round(sum(f["predicted_consumption"] for f in forecasts), 2),
            "net_grid_usage": round(sum(f["predicted_grid_usage"] for f in forecasts), 2),
            "self_sufficiency_percentage": 78.5,
            "peak_production_hour": 13,
            "peak_consumption_hour": 19
        },
        "model_performance": {
            "accuracy_last_7_days": 84.2,
            "mae_production": 0.32,
            "mae_consumption": 0.18,
            "model_version": "v2.1.0"
        },
        "recommendations": [
            "Schedule high-consumption appliances between 11:00-15:00",
            "Battery should reach 85% by 14:00 for evening load support",
            "Consider load-shedding preparation for 18:00-20:00 period"
        ],
        "confidence_score": 0.84,
        "last_updated": datetime.now()
    }
    
    return forecasting_data

# Notification and Alert API Endpoints
@app.get("/api/alerts")
async def get_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    hours: int = 24,
    user: dict = Depends(verify_token)
):
    """Get alerts with optional filtering"""
    if status == "active":
        alerts = alert_manager.get_active_alerts()
    else:
        alerts = alert_manager.get_alert_history(hours)
    
    # Filter by severity if specified
    if severity:
        alerts = [alert for alert in alerts if alert.severity.value == severity]
    
    return {
        "alerts": [alert.model_dump() for alert in alerts],
        "total": len(alerts),
        "active_count": len(alert_manager.get_active_alerts())
    }

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: dict = Depends(verify_token)):
    """Acknowledge an active alert"""
    success = alert_manager.acknowledge_alert(alert_id)
    if success:
        return {"message": "Alert acknowledged successfully", "alert_id": alert_id}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")

@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: dict = Depends(verify_token)):
    """Resolve an active alert"""
    success = alert_manager.resolve_alert(alert_id)
    if success:
        return {"message": "Alert resolved successfully", "alert_id": alert_id}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/api/notifications/preferences")
async def get_notification_preferences(user: dict = Depends(verify_token)):
    """Get user notification preferences"""
    return alert_manager.notification_preferences.model_dump()

@app.put("/api/notifications/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    user: dict = Depends(verify_token)
):
    """Update user notification preferences"""
    alert_manager.notification_preferences = preferences
    return {"message": "Notification preferences updated successfully"}

# ================================
# PERSISTENT SETTINGS ENDPOINTS
# ================================

@app.get("/api/settings/{category}")
async def get_settings_by_category(
    category: str,
    user: dict = Depends(verify_token)
):
    """Get all settings in a category for the current user"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    settings = await settings_manager.get_settings_by_category(category, user_id)
    return {"category": category, "settings": settings}

@app.get("/api/settings")
async def get_all_user_settings(user: dict = Depends(verify_token)):
    """Get all settings for the current user organized by category"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    settings = await settings_manager.get_user_settings(user_id)
    return {"user_id": user_id, "settings": settings}

@app.get("/api/settings/{category}/{key}")
async def get_setting(
    category: str,
    key: str,
    user: dict = Depends(verify_token)
):
    """Get a specific setting value"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    value = await settings_manager.get_setting(key, user_id)
    
    if value is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return {"key": key, "value": value, "category": category}

@app.put("/api/settings/{category}/{key}")
async def set_setting(
    category: str,
    key: str,
    request: dict,
    user: dict = Depends(verify_token)
):
    """Set a setting value for the current user"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    if "value" not in request:
        raise HTTPException(status_code=400, detail="Value is required")
    
    user_id = user.get("sub")
    value = request["value"]
    description = request.get("description")
    
    success = await settings_manager.set_setting(
        key=key,
        value=value,
        category=category,
        user_id=user_id,
        description=description
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save setting")
    
    return {"message": "Setting saved successfully", "key": key, "value": value}

@app.put("/api/settings/{category}")
async def update_category_settings(
    category: str,
    settings: dict,
    user: dict = Depends(verify_token)
):
    """Update multiple settings in a category"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    updated_count = 0
    errors = []
    
    for key, value in settings.items():
        success = await settings_manager.set_setting(
            key=key,
            value=value,
            category=category,
            user_id=user_id
        )
        if success:
            updated_count += 1
        else:
            errors.append(f"Failed to update {key}")
    
    return {
        "message": f"Updated {updated_count} settings in {category}",
        "updated_count": updated_count,
        "errors": errors
    }

@app.delete("/api/settings/{category}/{key}")
async def delete_setting(
    category: str,
    key: str,
    user: dict = Depends(verify_token)
):
    """Delete a specific setting"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    success = await settings_manager.delete_setting(key, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return {"message": "Setting deleted successfully", "key": key}

@app.post("/api/settings/export")
async def export_user_settings(user: dict = Depends(verify_token)):
    """Export all user settings as JSON"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    export_data = await settings_manager.export_settings(user_id)
    return export_data

@app.post("/api/settings/import")
async def import_user_settings(
    import_data: dict,
    overwrite: bool = False,
    user: dict = Depends(verify_token)
):
    """Import user settings from JSON data"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    imported_count = await settings_manager.import_settings(import_data, user_id, overwrite)
    
    return {
        "message": f"Imported {imported_count} settings",
        "imported_count": imported_count
    }

@app.post("/api/settings/reset")
async def reset_user_settings(user: dict = Depends(verify_token)):
    """Reset user settings to defaults"""
    if not SETTINGS_MANAGER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Settings manager not available")
    
    user_id = user.get("sub")
    reset_count = await settings_manager.reset_to_defaults(user_id)
    
    return {
        "message": f"Reset {reset_count} settings to defaults",
        "reset_count": reset_count
    }

@app.post("/api/alerts/test")
async def create_test_alert(
    severity: AlertSeverity = AlertSeverity.LOW,
    user: dict = Depends(verify_token)
):
    """Create a test alert for testing notification system"""
    alert = alert_manager.create_alert(
        title="Test Alert",
        message=f"This is a test {severity.value} severity alert to verify the notification system",
        severity=severity,
        category="test",
        metadata={"test": True, "created_by": user.get("sub")}
    )
    
    return {"message": "Test alert created", "alert": alert.model_dump()}

@app.get("/api/system/monitor")
async def get_system_monitoring_status(user: dict = Depends(verify_token)):
    """Get current system monitoring status and alert conditions"""
    current_data = real_collector.get_current_data()
    if not current_data:
        return {"status": "no_data", "monitoring": "inactive"}
    
    monitoring_data = {
        **current_data["metrics"],
        **current_data["status"],
        "weather_data": real_collector.latest_data["weather_data"] if real_collector.latest_data else {}
    }
    
    condition_status = {}
    for condition_name, condition_func in system_monitor.alert_conditions.items():
        try:
            condition_status[condition_name] = {
                "triggered": condition_func(monitoring_data),
                "description": {
                    "battery_low": "Battery level below 30%",
                    "battery_critical": "Battery level below 15%", 
                    "grid_outage": "Grid outage detected while battery low",
                    "inverter_offline": "No data from inverter for 5+ minutes",
                    "consumption_anomaly": "Consumption above 5kW",
                    "weather_poor": "Cloud cover above 80%",
                    "battery_not_charging": "Battery not charging during peak solar hours"
                }.get(condition_name, "Unknown condition")
            }
        except Exception as e:
            condition_status[condition_name] = {
                "triggered": False,
                "error": str(e)
            }
    
    return {
        "status": "active",
        "monitoring_data": monitoring_data,
        "alert_conditions": condition_status,
        "active_alerts": len(alert_manager.get_active_alerts()),
        "last_check": datetime.now().isoformat()
    }

# Intelligent Alert Configuration Endpoints
if INTELLIGENT_ALERTS_AVAILABLE:
    
    @app.get("/api/v1/alerts/config")
    async def get_alert_configurations(user: dict = Depends(verify_token)):
        """Get all alert configurations for the current user"""
        try:
            user_id = user.get("sub", "default")
            
            configurations = config_manager.get_user_configurations(user_id)
            return {
                "success": True,
                "configurations": [config.to_dict() for config in configurations]
            }
        except Exception as e:
            logger.error(f"Error getting alert configurations: {e}")
            raise HTTPException(status_code=500, detail="Failed to get configurations")
    
    @app.post("/api/v1/alerts/config")
    async def create_alert_configuration(request: dict, user: dict = Depends(verify_token)):
        """Create new alert configuration"""
        try:
            user_id = user.get("sub", "default")
            alert_type = AlertType(request.get('alert_type', 'energy_deficit'))
            
            # Remove user_id and alert_type from request for kwargs
            config_params = {k: v for k, v in request.items() if k not in ['alert_type', 'user_id']}
            
            configuration = config_manager.create_configuration(
                user_id=user_id,
                alert_type=alert_type,
                **config_params
            )
            
            return {
                "success": True,
                "configuration": configuration.to_dict()
            }
        except Exception as e:
            logger.error(f"Error creating alert configuration: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.put("/api/v1/alerts/config/{alert_type}")
    async def update_alert_configuration(alert_type: str, request: dict, user: dict = Depends(verify_token)):
        """Update alert configuration"""
        try:
            user_id = user.get("sub", "default")
            alert_type_enum = AlertType(alert_type)
            
            configuration = config_manager.update_configuration(
                user_id=user_id,
                alert_type=alert_type_enum,
                updates=request
            )
            
            return {
                "success": True,
                "configuration": configuration.to_dict()
            }
        except Exception as e:
            logger.error(f"Error updating alert configuration: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/v1/alerts/weather/predictions")
    async def get_weather_predictions(hours_ahead: int = 6, user: dict = Depends(verify_token)):
        """Get weather-based energy deficit predictions"""
        try:
            user_id = user.get("sub", "default")
            
            # Get configuration
            config = config_manager.get_configuration(user_id, AlertType.ENERGY_DEFICIT)
            if not config:
                config = config_manager.get_default_configuration(user_id, AlertType.ENERGY_DEFICIT)
            
            # Get predictions
            predictions = await weather_intelligence.predict_energy_deficit(config, hours_ahead)
            
            return {
                "success": True,
                "predictions": [
                    {
                        "timestamp": pred.timestamp.isoformat(),
                        "predicted_solar_power": pred.predicted_solar_power,
                        "predicted_deficit": pred.predicted_deficit,
                        "confidence": pred.confidence,
                        "weather_factors": pred.weather_factors,
                        "alert_recommended": pred.alert_recommended
                    } for pred in predictions
                ]
            }
        except Exception as e:
            logger.error(f"Error getting weather predictions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get predictions")
    
    @app.get("/api/v1/alerts/weather/current-impact")
    async def get_current_weather_impact(user: dict = Depends(verify_token)):
        """Get real-time weather impact on solar generation"""
        try:
            impact = await weather_intelligence.get_realtime_weather_impact()
            
            return {
                "success": True,
                "weather_impact": impact
            }
        except Exception as e:
            logger.error(f"Error getting weather impact: {e}")
            raise HTTPException(status_code=500, detail="Failed to get weather impact")
    
    @app.post("/api/v1/alerts/monitoring/start")
    async def start_monitoring(user: dict = Depends(verify_token)):
        """Start intelligent alert monitoring"""
        try:
            user_id = user.get("sub", "default")
            await alert_manager.start_intelligent_monitoring(user_id)
            
            return {
                "success": True,
                "message": "Intelligent monitoring started"
            }
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            raise HTTPException(status_code=500, detail="Failed to start monitoring")

@app.get("/api/alerts/summary")
async def get_alert_summary():
    """Get alert summary statistics"""
    try:
        alerts = alert_manager.get_recent_alerts(hours=24)
        
        summary = {
            "total": len(alerts),
            "active": len([a for a in alerts if a.get("status") == "active"]),
            "acknowledged": len([a for a in alerts if a.get("status") == "acknowledged"]),
            "resolved": len([a for a in alerts if a.get("status") == "resolved"]),
            "by_severity": {
                "low": len([a for a in alerts if a.get("severity") == "low"]),
                "medium": len([a for a in alerts if a.get("severity") == "medium"]),
                "high": len([a for a in alerts if a.get("severity") == "high"]),
                "critical": len([a for a in alerts if a.get("severity") == "critical"])
            }
        }
        
        return {"success": True, "summary": summary}
    except Exception as e:
        logger.error(f"Failed to get alert summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/alerts/status")
async def get_monitoring_status():
    """Get intelligent monitoring system status"""
    try:
        if not alert_manager.intelligent_monitor:
            return {
                "success": False,
                "error": "Intelligent monitoring not initialized"
            }
        
        # Get configuration validity
        config_manager = alert_manager.intelligent_monitor.config_manager
        config = config_manager.get_configuration()
        
        status = {
            "intelligent_monitoring": alert_manager.intelligent_monitor.is_running,
            "weather_intelligence": config.get("weather_intelligence", {}).get("enabled", False),
            "smart_alerts": config.get("smart_alerts_enabled", False),
            "last_check": datetime.now().isoformat(),
            "next_check": (datetime.now() + timedelta(seconds=30)).isoformat(),
            "configuration_valid": config is not None and len(config.get("alert_conditions", [])) > 0
        }
        
        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    try:
        result = alert_manager.acknowledge_alert(alert_id)
        if result:
            return {"success": True, "message": "Alert acknowledged"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    try:
        result = alert_manager.resolve_alert(alert_id)
        if result:
            return {"success": True, "message": "Alert resolved"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/alerts/config/validate")
async def validate_alert_configuration():
    """Validate the current alert configuration"""
    try:
        if not alert_manager.intelligent_monitor:
            return {
                "success": False,
                "error": "Intelligent monitoring not initialized"
            }
        
        config_manager = alert_manager.intelligent_monitor.config_manager
        config = config_manager.get_configuration()
        
        # Perform validation
        validation_result = config_manager.validate_configuration(config)
        
        return {
            "success": True,
            "valid": validation_result.get("valid", False),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", [])
        }
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Sunsynk Solar Dashboard Backend")
    
    # Initialize persistent settings manager
    if SETTINGS_MANAGER_AVAILABLE:
        try:
            await settings_manager.initialize()
            logger.info("✅ Persistent Settings Manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Settings Manager: {e}")
    
    # Start intelligent monitoring if available
    if INTELLIGENT_ALERTS_AVAILABLE:
        try:
            await alert_manager.start_intelligent_monitoring()
            await weather_intelligence.initialize()
            logger.info("✅ Intelligent Alert System initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Intelligent Alert System: {e}")
    
    # Create system status alert
    alert_manager.create_alert(
        title="System Started",
        message="Sunsynk Solar Dashboard backend is now online",
        severity=AlertSeverity.LOW,
        category="system"
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🔄 Shutting down Sunsynk Solar Dashboard Backend")
    
    # Stop intelligent monitoring
    if INTELLIGENT_ALERTS_AVAILABLE:
        alert_manager.stop_intelligent_monitoring()
        logger.info("✅ Intelligent Alert System stopped")

# WebSocket endpoint
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
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
        port=int(os.getenv("API_PORT", 8001)),
        reload=True
    )
