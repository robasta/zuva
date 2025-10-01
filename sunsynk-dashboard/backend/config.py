#!/usr/bin/env python3
"""
Sunsynk Solar Dashboard - Backend Configuration

Centralized configuration management for the FastAPI backend.
"""

import os
from typing import List
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"
    
    # Security
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = "sunsynk-admin-token"
    influxdb_org: str = "sunsynk"
    influxdb_bucket: str = "solar_data"
    
    # Logging
    log_level: str = "INFO"
    
    # Real-time Updates
    websocket_heartbeat_interval: int = 30  # seconds
    data_broadcast_interval: int = 5  # seconds
    
    # ML Analytics
    ml_model_training_interval: int = 6  # hours
    prediction_confidence_threshold: float = 0.7
    optimization_horizon_hours: int = 24
    
    # System Configuration
    battery_capacity_kwh: float = 5.0
    inverter_capacity_kw: float = 5.0
    inverter_efficiency: float = 0.95
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
        # Environment variable mappings
        fields = {
            'cors_origins': {'env': 'CORS_ORIGINS'},
            'jwt_secret_key': {'env': 'JWT_SECRET_KEY'},
            'influxdb_token': {'env': 'INFLUXDB_ADMIN_TOKEN'},
            'influxdb_org': {'env': 'INFLUXDB_ORG'},
            'influxdb_bucket': {'env': 'INFLUXDB_BUCKET'},
        }


# Global settings instance
settings = Settings()

# Helper function to parse CORS origins from environment
if isinstance(settings.cors_origins, str):
    settings.cors_origins = settings.cors_origins.split(',')
