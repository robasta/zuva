"""
Unit tests for enhanced data models.
Tests the extended models that build upon the existing Sunsynk Resource pattern.
"""
import pytest
import os
import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.models import EnhancedSolarMetrics, WeatherMetrics, SystemHealth, system_health


class TestEnhancedSolarMetrics:
    """Test cases for EnhancedSolarMetrics class."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_inverter_data = {
            'sn': '1029384756',
            'plant_id': '12345',
            'grid_power': 0.5,  # Importing 0.5kW from grid
            'battery_power': -0.3,  # Charging battery at 0.3kW
            'solar_power': 2.0,  # Generating 2.0kW from solar
            'battery_soc': 75.0,
            'grid_voltage': 235.0,
            'battery_voltage': 53.5,
            'battery_current': -5.6,
            'grid_frequency': 50.1,
            'battery_temp': 22.5,
            'daily_generation': 15.2,
            'daily_consumption': 12.8
        }
        
        self.sample_weather_data = {
            'temperature': 25.0,
            'cloud_cover': 30.0,
            'solar_irradiance': 750.0
        }
    
    def test_initialization(self):
        """Test EnhancedSolarMetrics initialization."""
        metrics = EnhancedSolarMetrics(self.sample_inverter_data)
        
        assert metrics.inverter_sn == '1029384756'
        assert metrics.plant_id == '12345'
        assert metrics.grid_power == 0.5
        assert metrics.battery_power == -0.3
        assert metrics.solar_power == 2.0
        assert metrics.battery_soc == 75.0
        assert isinstance(metrics.timestamp, datetime)
    
    def test_load_power_calculation(self):
        """Test load power calculation."""
        metrics = EnhancedSolarMetrics(self.sample_inverter_data)
        
        # Load = Solar + Grid - Battery charging
        # Load = 2.0 + 0.5 - 0.3 = 2.2kW
        expected_load = 2.0 + 0.5 - 0.3
        assert abs(metrics.load_power - expected_load) < 0.01
    
    def test_load_power_with_battery_discharge(self):
        """Test load power calculation with battery discharging."""
        data = self.sample_inverter_data.copy()
        data['battery_power'] = 0.8  # Battery discharging
        data['grid_power'] = -0.3  # Exporting to grid
        
        metrics = EnhancedSolarMetrics(data)
        
        # Load = Solar + Battery discharge - Grid export
        # Load = 2.0 + 0.8 - 0.3 = 2.5kW
        expected_load = 2.0 + 0.8 - 0.3
        assert abs(metrics.load_power - expected_load) < 0.01
    
    def test_efficiency_calculation(self):
        """Test system efficiency calculation."""
        metrics = EnhancedSolarMetrics(self.sample_inverter_data)
        
        # Efficiency = (Useful power out) / (Solar power in) * 100
        # Useful power = Load + Export = 2.2 + 0 = 2.2kW
        # Efficiency = 2.2 / 2.0 * 100 = 110% (capped at 100%)
        assert metrics.efficiency <= 100.0
        assert metrics.efficiency > 0.0
    
    def test_battery_runtime_calculation(self):
        """Test battery runtime calculation."""
        with patch.dict(os.environ, {'BATTERY_CAPACITY_KWH': '5.0'}):
            data = self.sample_inverter_data.copy()
            data['battery_power'] = 1.0  # Discharging at 1kW
            data['battery_soc'] = 80.0   # 80% charge
            
            metrics = EnhancedSolarMetrics(data)
            runtime = metrics.get_battery_runtime_hours()
            
            # Usable capacity: (80 - 15) / 100 * 5 = 3.25kWh
            # Runtime: 3.25 / 1.0 = 3.25 hours
            expected_runtime = 3.25
            assert abs(runtime - expected_runtime) < 0.1
    
    def test_battery_runtime_no_discharge(self):
        """Test battery runtime when not discharging."""
        data = self.sample_inverter_data.copy()
        data['battery_power'] = -0.5  # Charging
        
        metrics = EnhancedSolarMetrics(data)
        runtime = metrics.get_battery_runtime_hours()
        
        assert runtime == 0.0
    
    def test_geyser_runtime_calculation(self):
        """Test geyser runtime calculation."""
        with patch.dict(os.environ, {'BATTERY_CAPACITY_KWH': '5.0'}):
            data = self.sample_inverter_data.copy()
            data['battery_soc'] = 80.0
            
            metrics = EnhancedSolarMetrics(data)
            geyser_runtime = metrics.get_geyser_runtime_minutes(geyser_power_kw=3.0)
            
            # Available energy for geyser after other loads
            assert geyser_runtime >= 0
            assert isinstance(geyser_runtime, float)
    
    def test_cost_savings_calculation(self):
        """Test cost savings calculation."""
        metrics = EnhancedSolarMetrics(self.sample_inverter_data)
        savings = metrics.get_cost_savings_today()
        
        assert 'grid_cost_avoided' in savings
        assert 'grid_import_cost' in savings
        assert 'feed_in_earnings' in savings
        assert 'net_savings' in savings
        
        # All values should be non-negative
        for value in savings.values():
            assert value >= 0
    
    def test_weather_correlation(self):
        """Test weather correlation functionality."""
        metrics = EnhancedSolarMetrics(
            self.sample_inverter_data, 
            self.sample_weather_data
        )
        
        correlation = metrics.get_weather_correlation()
        assert 'temperature' in correlation
        assert 'cloud_cover' in correlation
        assert 'solar_irradiance' in correlation
        assert 'generation_efficiency' in correlation
    
    def test_database_record_format(self):
        """Test conversion to database record format."""
        metrics = EnhancedSolarMetrics(self.sample_inverter_data)
        record = metrics.to_database_record()
        
        required_fields = [
            'timestamp', 'inverter_sn', 'plant_id', 'grid_power',
            'battery_power', 'solar_power', 'battery_soc', 'load_power'
        ]
        
        for field in required_fields:
            assert field in record
        
        assert isinstance(record['timestamp'], datetime)


class TestWeatherMetrics:
    """Test cases for WeatherMetrics class."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_weather_data = {
            'location': 'Cape Town,ZA',
            'temperature': 25.0,
            'humidity': 65.0,
            'cloud_cover': 30.0,
            'uv_index': 8.0,
            'sunshine_hours': 6.5,
            'solar_irradiance': 750.0,
            'weather_condition': 'clear',
            'wind_speed': 5.2,
            'pressure': 1015.0
        }
    
    def test_initialization(self):
        """Test WeatherMetrics initialization."""
        weather = WeatherMetrics(self.sample_weather_data)
        
        assert weather.location == 'Cape Town,ZA'
        assert weather.temperature == 25.0
        assert weather.humidity == 65.0
        assert weather.cloud_cover == 30.0
        assert weather.solar_irradiance == 750.0
        assert isinstance(weather.timestamp, datetime)
    
    def test_solar_potential_calculation(self):
        """Test solar potential calculation."""
        weather = WeatherMetrics(self.sample_weather_data)
        
        # Solar potential should be based on cloud cover and irradiance
        assert 0 <= weather.solar_potential <= 100
        
        # Clear day with good irradiance should have high potential
        assert weather.solar_potential > 50
    
    def test_good_solar_day_detection(self):
        """Test good solar day detection."""
        weather = WeatherMetrics(self.sample_weather_data)
        
        # With 30% cloud cover, 750 W/m² irradiance, and 6.5h sunshine
        assert weather.is_good_solar_day() == True
        
        # Test bad solar day
        bad_weather = self.sample_weather_data.copy()
        bad_weather['cloud_cover'] = 90
        bad_weather['solar_irradiance'] = 150
        bad_weather['sunshine_hours'] = 2.0
        
        bad_weather_metrics = WeatherMetrics(bad_weather)
        assert bad_weather_metrics.is_good_solar_day() == False
    
    def test_weather_alert_conditions(self):
        """Test weather alert condition detection."""
        weather = WeatherMetrics(self.sample_weather_data)
        alerts = weather.get_weather_alert_conditions()
        
        assert 'low_sunshine' in alerts
        assert 'high_cloud_cover' in alerts
        assert 'low_irradiance' in alerts
        assert 'extreme_temperature' in alerts
        assert 'high_wind' in alerts
        
        # With good conditions, most alerts should be False
        assert alerts['low_sunshine'] == False
        assert alerts['high_cloud_cover'] == False
        assert alerts['low_irradiance'] == False
        assert alerts['extreme_temperature'] == False
        assert alerts['high_wind'] == False
    
    def test_database_record_format(self):
        """Test conversion to database record format."""
        weather = WeatherMetrics(self.sample_weather_data)
        record = weather.to_database_record()
        
        required_fields = [
            'timestamp', 'location', 'temperature', 'humidity',
            'cloud_cover', 'solar_irradiance', 'weather_condition'
        ]
        
        for field in required_fields:
            assert field in record


class TestSystemHealth:
    """Test cases for SystemHealth class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset system health for each test
        global system_health
        system_health = SystemHealth()
    
    def test_initialization(self):
        """Test SystemHealth initialization."""
        health = SystemHealth()
        
        assert health.api_connection_status == False
        assert health.database_connection_status == False
        assert health.error_count == 0
        assert health.warning_count == 0
        assert isinstance(health.timestamp, datetime)
    
    def test_status_updates(self):
        """Test status update methods."""
        health = SystemHealth()
        
        # Test API status update
        health.update_api_status(True)
        assert health.api_connection_status == True
        assert health.last_data_update is not None
        
        # Test database status update
        health.update_database_status(True)
        assert health.database_connection_status == True
    
    def test_error_counting(self):
        """Test error counting methods."""
        health = SystemHealth()
        
        initial_errors = health.error_count
        health.increment_error_count()
        assert health.error_count == initial_errors + 1
        
        initial_warnings = health.warning_count
        health.increment_warning_count()
        assert health.warning_count == initial_warnings + 1
    
    def test_health_score_calculation(self):
        """Test health score calculation."""
        health = SystemHealth()
        
        # Initially unhealthy (no connections)
        score = health.get_health_score()
        assert score < 100.0
        
        # Improve connections
        health.update_api_status(True)
        health.update_database_status(True)
        
        improved_score = health.get_health_score()
        assert improved_score > score
        assert improved_score <= 100.0
    
    def test_health_status(self):
        """Test health status determination."""
        health = SystemHealth()
        
        # Initially unhealthy
        assert health.is_healthy() == False
        
        # Make healthy
        health.update_api_status(True)
        health.update_database_status(True)
        
        assert health.is_healthy() == True
    
    def test_alert_generation(self):
        """Test alert generation."""
        health = SystemHealth()
        
        # Generate some alerts
        health.error_count = 25
        health.cpu_usage = 95.0
        
        alerts = health.get_alerts()
        
        assert len(alerts) > 0
        assert any('error count' in alert.lower() for alert in alerts)
        assert any('cpu usage' in alert.lower() for alert in alerts)
    
    def test_global_system_health_instance(self):
        """Test that the global system_health instance works correctly."""
        # Test that we can import and use the global instance
        from collector.models import system_health as global_health
        
        global_health.update_api_status(True)
        assert global_health.api_connection_status == True
        
        global_health.increment_error_count()
        assert global_health.error_count > 0


@pytest.fixture
def sample_inverter_data():
    """Fixture providing sample inverter data."""
    return {
        'sn': '1029384756',
        'plant_id': '12345',
        'grid_power': 0.5,
        'battery_power': -0.3,
        'solar_power': 2.0,
        'battery_soc': 75.0,
        'grid_voltage': 235.0,
        'battery_voltage': 53.5,
        'battery_current': -5.6,
        'grid_frequency': 50.1,
        'battery_temp': 22.5,
        'daily_generation': 15.2,
        'daily_consumption': 12.8
    }


@pytest.fixture
def sample_weather_data():
    """Fixture providing sample weather data."""
    return {
        'location': 'Cape Town,ZA',
        'temperature': 25.0,
        'humidity': 65.0,
        'cloud_cover': 30.0,
        'uv_index': 8.0,
        'sunshine_hours': 6.5,
        'solar_irradiance': 750.0,
        'weather_condition': 'clear',
        'wind_speed': 5.2,
        'pressure': 1015.0
    }


def test_enhanced_metrics_with_fixtures(sample_inverter_data, sample_weather_data):
    """Test EnhancedSolarMetrics using fixtures."""
    metrics = EnhancedSolarMetrics(sample_inverter_data, sample_weather_data)
    
    assert metrics.inverter_sn == '1029384756'
    assert metrics.weather_data == sample_weather_data
    
    correlation = metrics.get_weather_correlation()
    assert correlation['temperature'] == 25.0


def test_weather_metrics_with_fixtures(sample_weather_data):
    """Test WeatherMetrics using fixtures."""
    weather = WeatherMetrics(sample_weather_data)
    
    assert weather.location == 'Cape Town,ZA'
    assert weather.is_good_solar_day() == True