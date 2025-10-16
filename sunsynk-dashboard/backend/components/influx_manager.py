"""
InfluxDB Manager for Sunsynk Dashboard Phase 6
Handles time-series data storage and retrieval
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

class InfluxManager:
    """Manages InfluxDB operations for storing and retrieving solar data"""
    
    def __init__(self):
        # Get InfluxDB configuration from environment
        self.url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = os.getenv("INFLUXDB_TOKEN")
        self.org = os.getenv("INFLUXDB_ORG", "sunsynk")
        self.bucket = os.getenv("INFLUXDB_BUCKET", "solar_data")
        
        self.client = None
        self.write_api = None
        self.query_api = None
        
        if self.token:
            try:
                self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                logger.info("✅ InfluxDB client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize InfluxDB client: {e}")
                self.client = None
        else:
            logger.warning("⚠️ InfluxDB token not provided, database operations will be mocked")
    
    def is_available(self) -> bool:
        """Check if InfluxDB is available"""
        return self.client is not None
    
    def write_data_point(self, measurement: str, fields: Dict[str, Any], tags: Dict[str, str] = None) -> bool:
        """Write a single data point to InfluxDB"""
        if not self.is_available():
            logger.debug(f"📝 Mock write: {measurement} - {fields}")
            return True
            
        try:
            point = Point(measurement)
            
            # Add tags
            if tags:
                for key, value in tags.items():
                    point.tag(key, value)
            
            # Add fields
            for key, value in fields.items():
                if isinstance(value, (int, float)):
                    point.field(key, value)
                elif isinstance(value, str):
                    point.field(key, value)
                elif isinstance(value, bool):
                    point.field(key, value)
            
            # Set timestamp
            point.time(datetime.utcnow())
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"📝 Wrote data point: {measurement}")
            return True
            
        except Exception as e:
            logger.error(f"❌ InfluxDB connection error: {e}")
            return False
    
    def write_solar_data(self, data: Dict[str, Any]) -> bool:
        """Write solar inverter data to InfluxDB"""
        return self.write_data_point(
            measurement="solar_metrics",
            fields=data,
            tags={"source": "sunsynk_inverter"}
        )
    
    def query_historical_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Query historical data from InfluxDB"""
        if not self.is_available():
            # Check environment variable for mock data policy
            disable_mock_fallback = os.getenv('DISABLE_MOCK_FALLBACK', 'false').lower() == 'true'
            if disable_mock_fallback:
                logger.error("❌ InfluxDB unavailable and mock data fallback is disabled")
                return []
                
            logger.debug(f"📊 InfluxDB unavailable, generating mock data for last {hours} hours")
            return self._generate_mock_data(hours)
        
        try:
            # Query for the last N hours
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "solar_metrics")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query(org=self.org, query=query)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_point = {
                        "timestamp": record.get_time(),
                        "solar_power": record.values.get("solar_power", 0.0),
                        "battery_level": record.values.get("battery_level", 0.0),
                        "grid_consumption": record.values.get("grid_consumption", 0.0),
                        "consumption": record.values.get("consumption", 0.0),
                        "battery_voltage": record.values.get("battery_voltage", 0.0),
                        "battery_current": record.values.get("battery_current", 0.0),
                        "grid_voltage": record.values.get("grid_voltage", 0.0),
                        "grid_frequency": record.values.get("grid_frequency", 0.0),
                        "inverter_temp": record.values.get("inverter_temp", 0.0)
                    }
                    data_points.append(data_point)
            
            logger.info(f"📊 Retrieved {len(data_points)} data points from InfluxDB")
            return data_points
            
        except Exception as e:
            logger.error(f"❌ Failed to query historical data: {e}")
            
            # Check environment variable for mock data policy
            disable_mock_fallback = os.getenv('DISABLE_MOCK_FALLBACK', 'false').lower() == 'true'
            if disable_mock_fallback:
                logger.error("❌ InfluxDB query failed and mock data fallback is disabled")
                return []
                
            logger.warning("⚠️ InfluxDB query failed, generating mock data as fallback")
            return self._generate_mock_data(hours)
    
    def _generate_mock_data(self, hours: int) -> List[Dict[str, Any]]:
        """Generate mock data when InfluxDB is not available"""
        logger.warning(f"🎭 GENERATING MOCK DATA: {hours} hours of synthetic solar data")
        import random
        import math
        
        data_points = []
        now = datetime.now()
        
        for i in range(hours * 6):  # 6 points per hour (10-minute intervals)
            timestamp = now - timedelta(minutes=10 * i)
            hour = timestamp.hour
            
            # Simulate solar production based on time of day
            if 6 <= hour <= 18:
                solar_factor = math.sin(math.pi * (hour - 6) / 12)
                solar_power = 4.5 * solar_factor + random.uniform(-0.3, 0.3)
            else:
                solar_power = 0.0
            
            # Simulate consumption patterns
            if 6 <= hour <= 8 or 17 <= hour <= 22:  # Peak hours
                consumption = 2.0 + random.uniform(-0.5, 0.8)
            else:
                consumption = 1.2 + random.uniform(-0.3, 0.5)
            
            # Battery level simulation
            battery_level = 50 + 30 * math.sin(i * 0.1) + random.uniform(-5, 5)
            battery_level = max(10, min(95, battery_level))
            
            data_point = {
                "timestamp": timestamp,
                "solar_power": round(max(0, solar_power), 2),
                "battery_level": round(battery_level, 1),
                "grid_consumption": round(max(0, consumption - solar_power), 2),
                "consumption": round(consumption, 2),
                "battery_voltage": round(48.0 + random.uniform(-2, 2), 1),
                "battery_current": round(random.uniform(-20, 30), 1),
                "grid_voltage": round(230 + random.uniform(-10, 10), 1),
                "grid_frequency": round(50.0 + random.uniform(-0.1, 0.1), 2),
                "inverter_temp": round(35 + random.uniform(-5, 15), 1)
            }
            data_points.append(data_point)
        
        return sorted(data_points, key=lambda x: x["timestamp"])
    
    def query_timeseries_data(self, start_time: str = "-24h", resolution: str = "5m") -> List[Dict[str, Any]]:
        """Query timeseries data optimized for dashboard charts"""
        if not self.is_available():
            logger.debug(f"📊 Mock timeseries query: {start_time}")
            return []
            
        try:
            # Build the query for timeseries data
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r._measurement == "solar_metrics")
                |> filter(fn: (r) => r._field == "solar_power" or 
                                   r._field == "load_power" or 
                                   r._field == "consumption" or 
                                   r._field == "battery_soc" or 
                                   r._field == "battery_level")
                |> aggregateWindow(every: {resolution}, fn: mean, createEmpty: false)
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"])
            '''
            
            # Execute query
            result = self.query_api.query(org=self.org, query=query)
            
            data_points = []
            
            # Process results - handle both list and generator cases
            if hasattr(result, '__iter__'):
                for table in result:
                    if hasattr(table, 'records'):
                        for record in table.records:
                            # Extract values safely
                            timestamp = record.get_time()
                            values = record.values
                            
                            data_point = {
                                "timestamp": timestamp.isoformat() if timestamp else None,
                                "generation": values.get("solar_power", 0) or 0,
                                "consumption": values.get("load_power", values.get("consumption", 0)) or 0,
                                "battery_soc": values.get("battery_soc", values.get("battery_level", 0)) or 0,
                                "battery_level": values.get("battery_soc", values.get("battery_level", 0)) or 0
                            }
                            
                            # Only add valid data points
                            if data_point["timestamp"]:
                                data_points.append(data_point)
            
            logger.info(f"📊 Retrieved {len(data_points)} timeseries data points from InfluxDB")
            return sorted(data_points, key=lambda x: x["timestamp"])
            
        except Exception as e:
            logger.error(f"❌ Failed to query timeseries data: {e}")
            return []
    
    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """Get the most recent data point"""
        recent_data = self.query_historical_data(1)
        return recent_data[-1] if recent_data else None
    
    def close(self):
        """Close InfluxDB client connection"""
        if self.client:
            self.client.close()
            logger.info("📡 InfluxDB client connection closed")