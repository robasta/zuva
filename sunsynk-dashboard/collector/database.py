"""
Database abstraction layer for Sunsynk solar data storage.
Provides InfluxDB integration with time-series data schema.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import asyncio

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    from influxdb_client.rest import ApiException
except ImportError:
    # Fallback for development without InfluxDB
    InfluxDBClient = None
    Point = None
    SYNCHRONOUS = None
    ApiException = Exception

logger = logging.getLogger(__name__)


@dataclass
class SolarMetrics:
    """Solar power metrics data structure."""
    timestamp: datetime
    inverter_sn: str
    plant_id: str
    grid_power: float  # kW from/to grid (positive = from grid, negative = to grid)
    battery_power: float  # kW from/to battery (positive = discharge, negative = charge)
    solar_power: float  # kW from solar panels
    battery_soc: float  # % state of charge
    grid_voltage: float  # V
    battery_voltage: float  # V
    battery_current: float  # A
    load_power: float  # kW consumed by loads
    daily_generation: float  # kWh today
    daily_consumption: float  # kWh today
    hourly_consumption: float  # kWh this hour
    efficiency: float  # % efficiency
    battery_temp: float  # °C
    grid_frequency: float  # Hz
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for InfluxDB."""
        return asdict(self)


@dataclass
class WeatherData:
    """Weather data structure."""
    timestamp: datetime
    location: str
    temperature: float  # °C
    humidity: float  # %
    cloud_cover: float  # %
    uv_index: float  # UV index
    sunshine_hours: float  # hours projected for today
    solar_irradiance: float  # W/m²
    weather_condition: str  # sunny/cloudy/rain
    wind_speed: float  # m/s
    pressure: float  # hPa
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for InfluxDB."""
        return asdict(self)


@dataclass
class ConsumptionAnalysis:
    """Consumption analysis data structure."""
    timestamp: datetime
    analysis_type: str  # hourly/daily/monthly
    avg_consumption: float  # kW average
    peak_consumption: float  # kW peak
    min_consumption: float  # kW minimum
    battery_depletion_rate: float  # %/hour
    projected_runtime: float  # hours until 15%
    geyser_runtime_available: float  # minutes at current SOC
    cost_savings: float  # currency savings
    grid_import_cost: float  # currency cost
    solar_generation_value: float  # currency value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for InfluxDB."""
        return asdict(self)


@dataclass
class AlertData:
    """Alert data structure for database storage."""
    timestamp: datetime
    alert_id: str
    title: str
    message: str
    severity: str  # low/medium/high/critical
    status: str  # active/acknowledged/resolved
    category: str
    user_id: str = "default"
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for InfluxDB."""
        result = asdict(self)
        if self.metadata is None:
            result['metadata'] = {}
        return result


class DatabaseManager:
    """
    Database manager for InfluxDB time-series data storage.
    Handles solar metrics, weather data, and consumption analysis.
    """
    
    def __init__(
        self,
        url: str = None,
        token: str = None,
        org: str = None,
        bucket: str = None
    ):
        """Initialize database connection."""
        self.url = url or os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.token = token or os.getenv('INFLUXDB_TOKEN')
        self.org = org or os.getenv('INFLUXDB_ORG', 'sunsynk')
        self.bucket = bucket or os.getenv('INFLUXDB_BUCKET', 'solar_data')
        
        self.client = None
        self.write_api = None
        self.query_api = None
        
        if not self.token:
            logger.warning("InfluxDB token not provided, database operations will fail")
    
    async def connect(self) -> bool:
        """Establish database connection."""
        try:
            if InfluxDBClient is None:
                logger.error("InfluxDB client not available. Install influxdb-client package.")
                return False
            
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30_000,  # 30 seconds
                enable_gzip=True
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                logger.info(f"Connected to InfluxDB at {self.url}")
                await self._ensure_bucket_exists()
                return True
            else:
                logger.error(f"InfluxDB health check failed: {health.message}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False
    
    async def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if not."""
        try:
            buckets_api = self.client.buckets_api()
            buckets = buckets_api.find_buckets().buckets
            
            bucket_exists = any(bucket.name == self.bucket for bucket in buckets)
            
            if not bucket_exists:
                logger.info(f"Creating bucket: {self.bucket}")
                buckets_api.create_bucket(bucket_name=self.bucket, org=self.org)
                
        except Exception as e:
            logger.warning(f"Could not verify/create bucket: {e}")
    
    async def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")
    
    async def write_solar_metrics(self, metrics: SolarMetrics) -> bool:
        """Write solar metrics to database."""
        try:
            if not self.write_api:
                logger.error("Database not connected")
                return False
            
            point = (
                Point("solar_metrics")
                .tag("inverter_sn", metrics.inverter_sn)
                .tag("plant_id", str(metrics.plant_id))
                .field("grid_power", metrics.grid_power)
                .field("battery_power", metrics.battery_power)
                .field("solar_power", metrics.solar_power)
                .field("battery_soc", metrics.battery_soc)
                .field("grid_voltage", metrics.grid_voltage)
                .field("battery_voltage", metrics.battery_voltage)
                .field("battery_current", metrics.battery_current)
                .field("load_power", metrics.load_power)
                .field("daily_generation", metrics.daily_generation)
                .field("daily_consumption", metrics.daily_consumption)
                .field("hourly_consumption", metrics.hourly_consumption)
                .field("efficiency", metrics.efficiency)
                .field("battery_temp", metrics.battery_temp)
                .field("grid_frequency", metrics.grid_frequency)
                .time(metrics.timestamp)
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Solar metrics written for inverter {metrics.inverter_sn}")
            return True
            
        except ApiException as e:
            logger.error(f"InfluxDB API error writing solar metrics: {e}")
            return False
        except Exception as e:
            logger.error(f"Error writing solar metrics: {e}")
            return False
    
    async def write_weather_data(self, weather: WeatherData) -> bool:
        """Write weather data to database."""
        try:
            if not self.write_api:
                logger.error("Database not connected")
                return False
            
            point = (
                Point("weather_data")
                .tag("location", weather.location)
                .field("temperature", weather.temperature)
                .field("humidity", weather.humidity)
                .field("cloud_cover", weather.cloud_cover)
                .field("uv_index", weather.uv_index)
                .field("sunshine_hours", weather.sunshine_hours)
                .field("solar_irradiance", weather.solar_irradiance)
                .field("weather_condition", weather.weather_condition)
                .field("wind_speed", weather.wind_speed)
                .field("pressure", weather.pressure)
                .time(weather.timestamp)
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Weather data written for {weather.location}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing weather data: {e}")
            return False
    
    async def write_consumption_analysis(self, analysis: ConsumptionAnalysis) -> bool:
        """Write consumption analysis to database."""
        try:
            if not self.write_api:
                logger.error("Database not connected")
                return False
            
            point = (
                Point("consumption_analysis")
                .tag("analysis_type", analysis.analysis_type)
                .field("avg_consumption", analysis.avg_consumption)
                .field("peak_consumption", analysis.peak_consumption)
                .field("min_consumption", analysis.min_consumption)
                .field("battery_depletion_rate", analysis.battery_depletion_rate)
                .field("projected_runtime", analysis.projected_runtime)
                .field("geyser_runtime_available", analysis.geyser_runtime_available)
                .field("cost_savings", analysis.cost_savings)
                .field("grid_import_cost", analysis.grid_import_cost)
                .field("solar_generation_value", analysis.solar_generation_value)
                .time(analysis.timestamp)
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Consumption analysis written: {analysis.analysis_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing consumption analysis: {e}")
            return False
    
    async def get_latest_solar_metrics(self, inverter_sn: str = None) -> Optional[Dict[str, Any]]:
        """Get the latest solar metrics."""
        try:
            if not self.query_api:
                logger.error("Database not connected")
                return None
            
            filter_clause = f'|> filter(fn: (r) => r.inverter_sn == "{inverter_sn}")' if inverter_sn else ''
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "solar_metrics")
                {filter_clause}
                |> last()
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = self.query_api.query(query)
            
            for table in result:
                for record in table.records:
                    return {
                        'timestamp': record.get_time(),
                        'inverter_sn': record.get('inverter_sn'),
                        'plant_id': record.get('plant_id'),
                        'grid_power': record.get('grid_power'),
                        'battery_power': record.get('battery_power'),
                        'solar_power': record.get('solar_power'),
                        'battery_soc': record.get('battery_soc'),
                        'grid_voltage': record.get('grid_voltage'),
                        'battery_voltage': record.get('battery_voltage'),
                        'battery_current': record.get('battery_current'),
                        'load_power': record.get('load_power'),
                        'daily_generation': record.get('daily_generation'),
                        'daily_consumption': record.get('daily_consumption'),
                        'hourly_consumption': record.get('hourly_consumption'),
                        'efficiency': record.get('efficiency'),
                        'battery_temp': record.get('battery_temp'),
                        'grid_frequency': record.get('grid_frequency')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error querying latest solar metrics: {e}")
            return None
    
    async def get_historical_data(
        self, 
        measurement: str,
        start_time: str = "-24h",
        inverter_sn: str = None
    ) -> List[Dict[str, Any]]:
        """Get historical data for a measurement."""
        try:
            if not self.query_api:
                logger.error("Database not connected")
                return []
            
            filter_clause = f'|> filter(fn: (r) => r.inverter_sn == "{inverter_sn}")' if inverter_sn else ''
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r._measurement == "{measurement}")
                {filter_clause}
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query(query)
            data = []
            
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time(),
                        **{k: v for k, v in record.values.items() if not k.startswith('_')}
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error querying historical data: {e}")
            return []
    
    async def get_consumption_stats(self, period: str = "24h") -> Dict[str, float]:
        """Get consumption statistics for a period."""
        try:
            if not self.query_api:
                logger.error("Database not connected")
                return {}
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -{period})
                |> filter(fn: (r) => r._measurement == "solar_metrics")
                |> filter(fn: (r) => r._field == "load_power")
                |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
                |> yield(name: "hourly_avg")
            '''
            
            result = self.query_api.query(query)
            
            values = []
            for table in result:
                for record in table.records:
                    if record.get_value() is not None:
                        values.append(record.get_value())
            
            if not values:
                return {}
            
            return {
                'avg_consumption': sum(values) / len(values),
                'peak_consumption': max(values),
                'min_consumption': min(values),
                'total_hours': len(values)
            }
            
        except Exception as e:
            logger.error(f"Error querying consumption stats: {e}")
            return {}
    
    # Alert Storage Methods
    
    async def write_alert(self, alert: AlertData) -> bool:
        """Write alert to database."""
        try:
            if not self.write_api:
                logger.error("Database not connected")
                return False
            
            point = (
                Point("alerts")
                .tag("alert_id", alert.alert_id)
                .tag("severity", alert.severity)
                .tag("status", alert.status)
                .tag("category", alert.category)
                .tag("user_id", alert.user_id)
                .field("title", alert.title)
                .field("message", alert.message)
                .field("acknowledged_at", alert.acknowledged_at.isoformat() if alert.acknowledged_at else "")
                .field("resolved_at", alert.resolved_at.isoformat() if alert.resolved_at else "")
                .field("metadata", str(alert.metadata) if alert.metadata else "{}")
                .time(alert.timestamp)
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Alert written: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing alert: {e}")
            return False
    
    async def update_alert_status(self, alert_id: str, status: str, 
                                timestamp: datetime = None, user_id: str = "default") -> bool:
        """Update alert status in database."""
        try:
            if not self.write_api:
                logger.error("Database not connected")
                return False
            
            update_time = timestamp or datetime.now(timezone.utc)
            
            point = (
                Point("alert_status_updates")
                .tag("alert_id", alert_id)
                .tag("user_id", user_id)
                .field("new_status", status)
                .field("status_change", status)
                .time(update_time)
            )
            
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Alert status updated: {alert_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
            return False
    
    async def get_alerts(self, status: str = None, hours: int = 24, 
                        user_id: str = "default") -> List[Dict[str, Any]]:
        """Get alerts from database."""
        try:
            if not self.query_api:
                logger.error("Database not connected")
                return []
            
            status_filter = f'|> filter(fn: (r) => r.status == "{status}")' if status else ''
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "alerts")
                |> filter(fn: (r) => r.user_id == "{user_id}")
                {status_filter}
                |> sort(columns: ["_time"], desc: true)
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = self.query_api.query(query)
            alerts = []
            
            for table in result:
                for record in table.records:
                    alert_data = {
                        'id': record.get('alert_id'),
                        'title': record.get('title'),
                        'message': record.get('message'),
                        'severity': record.get('severity'),
                        'status': record.get('status'),
                        'category': record.get('category'),
                        'timestamp': record.get_time().isoformat(),
                        'acknowledged_at': record.get('acknowledged_at') if record.get('acknowledged_at') else None,
                        'resolved_at': record.get('resolved_at') if record.get('resolved_at') else None,
                        'metadata': eval(record.get('metadata', '{}')) if record.get('metadata') and record.get('metadata') != '{}' else {}
                    }
                    alerts.append(alert_data)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error querying alerts: {e}")
            return []
    
    async def get_active_alerts(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """Get active alerts from database."""
        return await self.get_alerts(status="active", hours=24*7, user_id=user_id)  # Last week of active alerts
    
    async def cleanup_old_alerts(self, retention_days: int = 90) -> bool:
        """Clean up old resolved alerts."""
        try:
            if not self.client:
                logger.error("Database not connected")
                return False
            
            # Delete alerts older than retention period
            delete_api = self.client.delete_api()
            start = f"-{retention_days}d"
            stop = datetime.now(timezone.utc)
            
            delete_api.delete(
                start=start,
                stop=stop,
                predicate='_measurement="alerts" AND status="resolved"',
                bucket=self.bucket,
                org=self.org
            )
            
            logger.info(f"Cleaned up alerts older than {retention_days} days")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
            return False
    
    async def get_timeseries_data(self, start_time: str = "-24h", 
                                resolution: str = "5m") -> List[Dict[str, Any]]:
        """Get time series data for dashboard graphs."""
        try:
            if not self.query_api:
                logger.error("Database not connected")
                return []
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r._measurement == "solar_metrics")
                |> filter(fn: (r) => r._field == "solar_power" or r._field == "load_power" or r._field == "consumption" or r._field == "battery_soc")
                |> aggregateWindow(every: {resolution}, fn: mean, createEmpty: false)
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"])
            '''
            
            result = self.query_api.query(query)
            data = []
            
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time().isoformat(),
                        'generation': record.get('solar_power', 0),
                        'consumption': record.get('consumption', record.get('load_power', 0)),
                        'battery_soc': record.get('battery_soc', 0),
                        'battery_level': record.get('battery_soc', 0)  # Alias for compatibility
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error querying timeseries data: {e}")
            return []


# Singleton instance for global use
db_manager = DatabaseManager()


async def initialize_database() -> bool:
    """Initialize the global database manager."""
    return await db_manager.connect()


async def cleanup_database():
    """Cleanup the global database manager."""
    await db_manager.close()