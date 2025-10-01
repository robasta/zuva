"""
Extended data models for Sunsynk solar dashboard.
Builds upon the existing Resource pattern from the base client.
"""
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Add the parent directory to the path to import sunsynk modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sunsynk.resource import Resource
from sunsynk.battery import Battery as BaseBattery
from sunsynk.grid import Grid as BaseGrid
from sunsynk.input import Input as BaseInput
from sunsynk.output import Output as BaseOutput
from sunsynk.inverter import Inverter as BaseInverter


class EnhancedSolarMetrics(Resource):
    """Enhanced solar metrics with additional calculations and database persistence."""
    
    def __init__(self, inverter_data: Dict[str, Any], weather_data: Optional[Dict[str, Any]] = None):
        """Initialize enhanced solar metrics from raw API data."""
        self.timestamp = datetime.now(timezone.utc)
        self.inverter_sn = inverter_data.get('sn', '')
        self.plant_id = str(inverter_data.get('plant_id', ''))
        
        # Raw power measurements
        self.grid_power = float(inverter_data.get('grid_power', 0))  # kW
        self.battery_power = float(inverter_data.get('battery_power', 0))  # kW
        self.solar_power = float(inverter_data.get('solar_power', 0))  # kW
        self.battery_soc = float(inverter_data.get('battery_soc', 0))  # %
        
        # Voltage and current measurements
        self.grid_voltage = float(inverter_data.get('grid_voltage', 0))  # V
        self.battery_voltage = float(inverter_data.get('battery_voltage', 0))  # V
        self.battery_current = float(inverter_data.get('battery_current', 0))  # A
        self.grid_frequency = float(inverter_data.get('grid_frequency', 50.0))  # Hz
        self.battery_temp = float(inverter_data.get('battery_temp', 20.0))  # °C
        
        # Daily totals
        self.daily_generation = float(inverter_data.get('daily_generation', 0))  # kWh
        self.daily_consumption = float(inverter_data.get('daily_consumption', 0))  # kWh
        
        # Calculated fields
        self.load_power = self._calculate_load_power()
        self.hourly_consumption = self._calculate_hourly_consumption()
        self.efficiency = self._calculate_efficiency()
        
        # Weather correlation
        self.weather_data = weather_data
        
        # Financial calculations
        self.cost_per_kwh_grid = float(os.getenv('GRID_COST_PER_KWH', '2.50'))  # Default R2.50/kWh
        self.feed_in_tariff = float(os.getenv('FEED_IN_TARIFF', '0.80'))  # Default R0.80/kWh
    
    def _calculate_load_power(self) -> float:
        """Calculate current load power consumption."""
        # Load = Solar generation + Battery discharge - Grid export + Grid import
        load = self.solar_power
        
        if self.battery_power > 0:  # Battery discharging
            load += self.battery_power
        else:  # Battery charging
            load -= abs(self.battery_power)
        
        if self.grid_power > 0:  # Importing from grid
            load += self.grid_power
        else:  # Exporting to grid
            load -= abs(self.grid_power)
        
        return max(0, load)  # Load cannot be negative
    
    def _calculate_hourly_consumption(self) -> float:
        """Estimate hourly consumption based on current load."""
        # This is an approximation - actual hourly consumption would need historical data
        return self.load_power  # Assume current load continues for the hour
    
    def _calculate_efficiency(self) -> float:
        """Calculate system efficiency percentage."""
        if self.solar_power <= 0:
            return 0.0
        
        # Efficiency = (Useful power out) / (Solar power in) * 100
        useful_power = self.load_power + max(0, -self.grid_power)  # Load + export
        return min(100.0, (useful_power / self.solar_power) * 100)
    
    def get_battery_runtime_hours(self, target_soc: float = 15.0) -> float:
        """Calculate battery runtime hours until target SOC."""
        if self.battery_power <= 0 or self.battery_soc <= target_soc:
            return 0.0
        
        # Usable capacity from current SOC to target SOC
        usable_soc = self.battery_soc - target_soc
        
        # Estimate battery capacity (this could be configurable)
        battery_capacity_kwh = float(os.getenv('BATTERY_CAPACITY_KWH', '5.0'))
        usable_energy = (usable_soc / 100) * battery_capacity_kwh
        
        # Runtime = usable energy / discharge rate
        return usable_energy / self.battery_power
    
    def get_geyser_runtime_minutes(self, geyser_power_kw: float = 3.0) -> float:
        """Calculate available geyser runtime in minutes without dropping below 15% SOC."""
        runtime_hours = self.get_battery_runtime_hours()
        if runtime_hours <= 0:
            return 0.0
        
        # Available energy for geyser
        battery_capacity_kwh = float(os.getenv('BATTERY_CAPACITY_KWH', '5.0'))
        usable_energy = (self.battery_soc - 15.0) / 100 * battery_capacity_kwh
        
        # Account for other loads
        other_load_power = max(0, self.load_power - geyser_power_kw)
        available_for_geyser = usable_energy - (other_load_power * runtime_hours)
        
        if available_for_geyser <= 0:
            return 0.0
        
        return (available_for_geyser / geyser_power_kw) * 60  # Convert to minutes
    
    def get_cost_savings_today(self) -> Dict[str, float]:
        """Calculate cost savings for today."""
        grid_cost_avoided = self.daily_generation * self.cost_per_kwh_grid
        grid_import_cost = max(0, self.daily_consumption - self.daily_generation) * self.cost_per_kwh_grid
        feed_in_earnings = max(0, self.daily_generation - self.daily_consumption) * self.feed_in_tariff
        
        return {
            'grid_cost_avoided': grid_cost_avoided,
            'grid_import_cost': grid_import_cost,
            'feed_in_earnings': feed_in_earnings,
            'net_savings': grid_cost_avoided + feed_in_earnings - grid_import_cost
        }
    
    def get_weather_correlation(self) -> Dict[str, Any]:
        """Get weather correlation data if available."""
        if not self.weather_data:
            return {}
        
        return {
            'temperature': self.weather_data.get('temperature'),
            'cloud_cover': self.weather_data.get('cloud_cover'),
            'solar_irradiance': self.weather_data.get('solar_irradiance'),
            'generation_efficiency': self._calculate_weather_efficiency()
        }
    
    def _calculate_weather_efficiency(self) -> float:
        """Calculate generation efficiency based on weather conditions."""
        if not self.weather_data:
            return 0.0
        
        irradiance = self.weather_data.get('solar_irradiance', 0)
        if irradiance <= 0:
            return 0.0
        
        # Theoretical max power based on irradiance (assuming 1kW/m² = rated power)
        inverter_capacity_kw = float(os.getenv('INVERTER_CAPACITY_KW', '5.0'))
        theoretical_power = (irradiance / 1000) * inverter_capacity_kw
        
        if theoretical_power <= 0:
            return 0.0
        
        return min(100.0, (self.solar_power / theoretical_power) * 100)
    
    def to_database_record(self) -> Dict[str, Any]:
        """Convert to database record format."""
        return {
            'timestamp': self.timestamp,
            'inverter_sn': self.inverter_sn,
            'plant_id': self.plant_id,
            'grid_power': self.grid_power,
            'battery_power': self.battery_power,
            'solar_power': self.solar_power,
            'battery_soc': self.battery_soc,
            'grid_voltage': self.grid_voltage,
            'battery_voltage': self.battery_voltage,
            'battery_current': self.battery_current,
            'load_power': self.load_power,
            'daily_generation': self.daily_generation,
            'daily_consumption': self.daily_consumption,
            'hourly_consumption': self.hourly_consumption,
            'efficiency': self.efficiency,
            'battery_temp': self.battery_temp,
            'grid_frequency': self.grid_frequency
        }


class WeatherMetrics(Resource):
    """Weather metrics with solar correlation capabilities."""
    
    def __init__(self, weather_data: Dict[str, Any]):
        """Initialize weather metrics from API data."""
        self.timestamp = datetime.now(timezone.utc)
        self.location = weather_data.get('location', 'Unknown')
        self.temperature = float(weather_data.get('temperature', 0))  # °C
        self.humidity = float(weather_data.get('humidity', 0))  # %
        self.cloud_cover = float(weather_data.get('cloud_cover', 0))  # %
        self.uv_index = float(weather_data.get('uv_index', 0))
        self.sunshine_hours = float(weather_data.get('sunshine_hours', 0))
        self.solar_irradiance = float(weather_data.get('solar_irradiance', 0))  # W/m²
        self.weather_condition = weather_data.get('weather_condition', 'unknown')
        self.wind_speed = float(weather_data.get('wind_speed', 0))  # m/s
        self.pressure = float(weather_data.get('pressure', 1013.25))  # hPa
        
        # Calculate derived metrics
        self.solar_potential = self._calculate_solar_potential()
        self.generation_forecast = self._forecast_generation()
    
    def _calculate_solar_potential(self) -> float:
        """Calculate solar generation potential (0-100%)."""
        # Base potential on cloud cover and solar irradiance
        cloud_factor = max(0, 100 - self.cloud_cover) / 100
        irradiance_factor = min(1.0, self.solar_irradiance / 1000)  # Normalize to 1000 W/m²
        
        return min(100.0, (cloud_factor * irradiance_factor * 100))
    
    def _forecast_generation(self) -> float:
        """Forecast generation for the rest of the day."""
        # Simple forecast based on current conditions and sunshine hours
        inverter_capacity_kw = float(os.getenv('INVERTER_CAPACITY_KW', '5.0'))
        return self.sunshine_hours * inverter_capacity_kw * (self.solar_potential / 100)
    
    def is_good_solar_day(self) -> bool:
        """Determine if today is a good solar generation day."""
        return (
            self.cloud_cover < 50 and  # Less than 50% cloud cover
            self.solar_irradiance > 300 and  # At least 300 W/m²
            self.sunshine_hours > 4  # At least 4 hours of sunshine
        )
    
    def get_weather_alert_conditions(self) -> Dict[str, bool]:
        """Check for weather conditions that warrant alerts."""
        return {
            'low_sunshine': self.sunshine_hours < 4,
            'high_cloud_cover': self.cloud_cover > 80,
            'low_irradiance': self.solar_irradiance < 200,
            'extreme_temperature': self.temperature < 0 or self.temperature > 45,
            'high_wind': self.wind_speed > 15  # m/s
        }
    
    def to_database_record(self) -> Dict[str, Any]:
        """Convert to database record format."""
        return {
            'timestamp': self.timestamp,
            'location': self.location,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'cloud_cover': self.cloud_cover,
            'uv_index': self.uv_index,
            'sunshine_hours': self.sunshine_hours,
            'solar_irradiance': self.solar_irradiance,
            'weather_condition': self.weather_condition,
            'wind_speed': self.wind_speed,
            'pressure': self.pressure
        }


class SystemHealth(Resource):
    """System health and status monitoring."""
    
    def __init__(self):
        """Initialize system health metrics."""
        self.timestamp = datetime.now(timezone.utc)
        self.api_connection_status = False
        self.database_connection_status = False
        self.last_data_update = None
        self.last_analytics_run = None
        self.error_count = 0
        self.warning_count = 0
        self.data_collection_failures = 0
        self.notification_failures = 0
        self.analytics_failures = 0
        
        # Performance metrics
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.disk_usage = 0.0
        self.network_latency = 0.0
    
    def update_api_status(self, connected: bool):
        """Update API connection status."""
        self.api_connection_status = connected
        if connected:
            self.last_data_update = datetime.now(timezone.utc)
    
    def update_database_status(self, connected: bool):
        """Update database connection status."""
        self.database_connection_status = connected
    
    def increment_error_count(self):
        """Increment error counter."""
        self.error_count += 1
    
    def increment_warning_count(self):
        """Increment warning counter."""
        self.warning_count += 1
    
    def increment_data_collection_failure(self):
        """Increment data collection failure counter."""
        self.data_collection_failures += 1
    
    def increment_notification_failure(self):
        """Increment notification failure counter."""
        self.notification_failures += 1
    
    def increment_analytics_failure(self):
        """Increment analytics failure counter."""
        self.analytics_failures += 1
    
    def get_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        score = 100.0
        
        # Connection status
        if not self.api_connection_status:
            score -= 30.0
        if not self.database_connection_status:
            score -= 20.0
        
        # Data freshness
        if self.last_data_update:
            age_minutes = (datetime.now(timezone.utc) - self.last_data_update).total_seconds() / 60
            if age_minutes > 5:  # Data older than 5 minutes
                score -= min(30.0, age_minutes * 2)
        
        # Error rates
        if self.error_count > 10:
            score -= min(20.0, self.error_count - 10)
        
        # Resource usage
        if self.cpu_usage > 80:
            score -= 10.0
        if self.memory_usage > 90:
            score -= 10.0
        if self.disk_usage > 90:
            score -= 10.0
        
        return max(0.0, score)
    
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.get_health_score() > 70.0
    
    def get_alerts(self) -> List[str]:
        """Get list of current alerts."""
        alerts = []
        
        if not self.api_connection_status:
            alerts.append("Sunsynk API connection failed")
        
        if not self.database_connection_status:
            alerts.append("Database connection failed")
        
        if self.last_data_update:
            age_minutes = (datetime.now(timezone.utc) - self.last_data_update).total_seconds() / 60
            if age_minutes > 10:
                alerts.append(f"Data collection stale ({age_minutes:.1f} minutes)")
        
        if self.error_count > 20:
            alerts.append(f"High error count ({self.error_count})")
        
        if self.cpu_usage > 90:
            alerts.append(f"High CPU usage ({self.cpu_usage:.1f}%)")
        
        if self.memory_usage > 95:
            alerts.append(f"High memory usage ({self.memory_usage:.1f}%)")
        
        if self.disk_usage > 95:
            alerts.append(f"High disk usage ({self.disk_usage:.1f}%)")
        
        return alerts


# Global system health instance
system_health = SystemHealth()