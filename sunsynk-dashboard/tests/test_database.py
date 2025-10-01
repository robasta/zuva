"""
Unit tests for database functionality.
Tests the InfluxDB integration and data storage operations.
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.database import DatabaseManager, SolarMetrics, WeatherData, ConsumptionAnalysis


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.db_manager = DatabaseManager(
            url='http://localhost:8086',
            token='test-token',
            org='test-org',
            bucket='test-bucket'
        )
    
    def test_initialization(self):
        """Test DatabaseManager initialization."""
        assert self.db_manager.url == 'http://localhost:8086'
        assert self.db_manager.token == 'test-token'
        assert self.db_manager.org == 'test-org'
        assert self.db_manager.bucket == 'test-bucket'
        assert self.db_manager.client is None
    
    def test_initialization_from_env(self):
        """Test DatabaseManager initialization from environment variables."""
        with patch.dict(os.environ, {
            'INFLUXDB_URL': 'http://env-host:8086',
            'INFLUXDB_TOKEN': 'env-token',
            'INFLUXDB_ORG': 'env-org',
            'INFLUXDB_BUCKET': 'env-bucket'
        }):
            db = DatabaseManager()
            assert db.url == 'http://env-host:8086'
            assert db.token == 'env-token'
            assert db.org == 'env-org'
            assert db.bucket == 'env-bucket'
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful database connection."""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        
        with patch('collector.database.InfluxDBClient', return_value=mock_client):
            with patch.object(self.db_manager, '_ensure_bucket_exists', new_callable=AsyncMock):
                result = await self.db_manager.connect()
                
                assert result is True
                assert self.db_manager.client == mock_client
                assert self.db_manager.write_api is not None
                assert self.db_manager.query_api is not None
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test database connection failure."""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "fail"
        mock_health.message = "Connection failed"
        mock_client.health.return_value = mock_health
        
        with patch('collector.database.InfluxDBClient', return_value=mock_client):
            result = await self.db_manager.connect()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_connect_influxdb_unavailable(self):
        """Test connection when InfluxDB client is not available."""
        with patch('collector.database.InfluxDBClient', None):
            result = await self.db_manager.connect()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_write_solar_metrics_success(self):
        """Test successful solar metrics writing."""
        # Set up connected database manager
        self.db_manager.write_api = Mock()
        
        solar_metrics = SolarMetrics(
            timestamp=datetime.now(timezone.utc),
            inverter_sn='1029384756',
            plant_id='12345',
            grid_power=0.5,
            battery_power=-0.3,
            solar_power=2.0,
            battery_soc=75.0,
            grid_voltage=235.0,
            battery_voltage=53.5,
            battery_current=-5.6,
            load_power=2.2,
            daily_generation=15.2,
            daily_consumption=12.8,
            hourly_consumption=2.2,
            efficiency=95.0,
            battery_temp=22.5,
            grid_frequency=50.1
        )
        
        result = await self.db_manager.write_solar_metrics(solar_metrics)
        
        assert result is True
        self.db_manager.write_api.write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_solar_metrics_failure(self):
        """Test solar metrics writing failure."""
        self.db_manager.write_api = Mock()
        self.db_manager.write_api.write.side_effect = Exception("Write failed")
        
        solar_metrics = SolarMetrics(
            timestamp=datetime.now(timezone.utc),
            inverter_sn='1029384756',
            plant_id='12345',
            grid_power=0.5,
            battery_power=-0.3,
            solar_power=2.0,
            battery_soc=75.0,
            grid_voltage=235.0,
            battery_voltage=53.5,
            battery_current=-5.6,
            load_power=2.2,
            daily_generation=15.2,
            daily_consumption=12.8,
            hourly_consumption=2.2,
            efficiency=95.0,
            battery_temp=22.5,
            grid_frequency=50.1
        )
        
        result = await self.db_manager.write_solar_metrics(solar_metrics)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_write_weather_data_success(self):
        """Test successful weather data writing."""
        self.db_manager.write_api = Mock()
        
        weather_data = WeatherData(
            timestamp=datetime.now(timezone.utc),
            location='Cape Town,ZA',
            temperature=25.0,
            humidity=65.0,
            cloud_cover=30.0,
            uv_index=8.0,
            sunshine_hours=6.5,
            solar_irradiance=750.0,
            weather_condition='clear',
            wind_speed=5.2,
            pressure=1015.0
        )
        
        result = await self.db_manager.write_weather_data(weather_data)
        
        assert result is True
        self.db_manager.write_api.write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_consumption_analysis_success(self):
        """Test successful consumption analysis writing."""
        self.db_manager.write_api = Mock()
        
        consumption_analysis = ConsumptionAnalysis(
            timestamp=datetime.now(timezone.utc),
            analysis_type='hourly',
            avg_consumption=2.0,
            peak_consumption=3.5,
            min_consumption=0.8,
            battery_depletion_rate=5.0,
            projected_runtime=4.5,
            geyser_runtime_available=45.0,
            cost_savings=25.50,
            grid_import_cost=12.75,
            solar_generation_value=38.25
        )
        
        result = await self.db_manager.write_consumption_analysis(consumption_analysis)
        
        assert result is True
        self.db_manager.write_api.write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_latest_solar_metrics_success(self):
        """Test successful retrieval of latest solar metrics."""
        # Mock query result
        mock_record = Mock()
        mock_record.get_time.return_value = datetime.now(timezone.utc)
        mock_record.get.side_effect = lambda key: {
            'inverter_sn': '1029384756',
            'plant_id': '12345',
            'grid_power': 0.5,
            'battery_power': -0.3,
            'solar_power': 2.0,
            'battery_soc': 75.0
        }.get(key)
        
        mock_table = Mock()
        mock_table.records = [mock_record]
        
        mock_query_api = Mock()
        mock_query_api.query.return_value = [mock_table]
        self.db_manager.query_api = mock_query_api
        
        result = await self.db_manager.get_latest_solar_metrics('1029384756')
        
        assert result is not None
        assert result['inverter_sn'] == '1029384756'
        assert result['grid_power'] == 0.5
    
    @pytest.mark.asyncio
    async def test_get_latest_solar_metrics_no_data(self):
        """Test retrieval when no data is available."""
        mock_query_api = Mock()
        mock_query_api.query.return_value = []
        self.db_manager.query_api = mock_query_api
        
        result = await self.db_manager.get_latest_solar_metrics('1029384756')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_historical_data_success(self):
        """Test successful retrieval of historical data."""
        # Mock query result
        mock_record1 = Mock()
        mock_record1.get_time.return_value = datetime.now(timezone.utc)
        mock_record1.values = {
            'inverter_sn': '1029384756',
            'grid_power': 0.5,
            '_time': datetime.now(timezone.utc),
            '_measurement': 'solar_metrics'
        }
        
        mock_record2 = Mock()
        mock_record2.get_time.return_value = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_record2.values = {
            'inverter_sn': '1029384756',
            'grid_power': 0.3,
            '_time': datetime.now(timezone.utc) - timedelta(hours=1),
            '_measurement': 'solar_metrics'
        }
        
        mock_table = Mock()
        mock_table.records = [mock_record1, mock_record2]
        
        mock_query_api = Mock()
        mock_query_api.query.return_value = [mock_table]
        self.db_manager.query_api = mock_query_api
        
        result = await self.db_manager.get_historical_data('solar_metrics', '-24h', '1029384756')
        
        assert len(result) == 2
        assert result[0]['grid_power'] == 0.5
        assert result[1]['grid_power'] == 0.3
    
    @pytest.mark.asyncio
    async def test_get_consumption_stats_success(self):
        """Test successful retrieval of consumption statistics."""
        # Mock query result
        mock_record1 = Mock()
        mock_record1.get_value.return_value = 2.0
        
        mock_record2 = Mock()
        mock_record2.get_value.return_value = 1.5
        
        mock_record3 = Mock()
        mock_record3.get_value.return_value = 3.0
        
        mock_table = Mock()
        mock_table.records = [mock_record1, mock_record2, mock_record3]
        
        mock_query_api = Mock()
        mock_query_api.query.return_value = [mock_table]
        self.db_manager.query_api = mock_query_api
        
        result = await self.db_manager.get_consumption_stats('24h')
        
        assert 'avg_consumption' in result
        assert 'peak_consumption' in result
        assert 'min_consumption' in result
        assert 'total_hours' in result
        
        assert result['avg_consumption'] == 2.167  # (2.0 + 1.5 + 3.0) / 3
        assert result['peak_consumption'] == 3.0
        assert result['min_consumption'] == 1.5
        assert result['total_hours'] == 3
    
    @pytest.mark.asyncio
    async def test_get_consumption_stats_no_data(self):
        """Test consumption stats when no data is available."""
        mock_table = Mock()
        mock_table.records = []
        
        mock_query_api = Mock()
        mock_query_api.query.return_value = [mock_table]
        self.db_manager.query_api = mock_query_api
        
        result = await self.db_manager.get_consumption_stats('24h')
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test database connection cleanup."""
        mock_client = Mock()
        self.db_manager.client = mock_client
        
        await self.db_manager.close()
        
        mock_client.close.assert_called_once()


class TestDataStructures:
    """Test cases for data structure classes."""
    
    def test_solar_metrics_creation(self):
        """Test SolarMetrics data structure creation."""
        timestamp = datetime.now(timezone.utc)
        
        metrics = SolarMetrics(
            timestamp=timestamp,
            inverter_sn='1029384756',
            plant_id='12345',
            grid_power=0.5,
            battery_power=-0.3,
            solar_power=2.0,
            battery_soc=75.0,
            grid_voltage=235.0,
            battery_voltage=53.5,
            battery_current=-5.6,
            load_power=2.2,
            daily_generation=15.2,
            daily_consumption=12.8,
            hourly_consumption=2.2,
            efficiency=95.0,
            battery_temp=22.5,
            grid_frequency=50.1
        )
        
        assert metrics.timestamp == timestamp
        assert metrics.inverter_sn == '1029384756'
        assert metrics.grid_power == 0.5
        assert metrics.battery_soc == 75.0
        
        # Test to_dict method
        data_dict = metrics.to_dict()
        assert 'timestamp' in data_dict
        assert 'inverter_sn' in data_dict
        assert data_dict['grid_power'] == 0.5
    
    def test_weather_data_creation(self):
        """Test WeatherData data structure creation."""
        timestamp = datetime.now(timezone.utc)
        
        weather = WeatherData(
            timestamp=timestamp,
            location='Cape Town,ZA',
            temperature=25.0,
            humidity=65.0,
            cloud_cover=30.0,
            uv_index=8.0,
            sunshine_hours=6.5,
            solar_irradiance=750.0,
            weather_condition='clear',
            wind_speed=5.2,
            pressure=1015.0
        )
        
        assert weather.timestamp == timestamp
        assert weather.location == 'Cape Town,ZA'
        assert weather.temperature == 25.0
        assert weather.solar_irradiance == 750.0
        
        # Test to_dict method
        data_dict = weather.to_dict()
        assert 'timestamp' in data_dict
        assert 'location' in data_dict
        assert data_dict['temperature'] == 25.0
    
    def test_consumption_analysis_creation(self):
        """Test ConsumptionAnalysis data structure creation."""
        timestamp = datetime.now(timezone.utc)
        
        analysis = ConsumptionAnalysis(
            timestamp=timestamp,
            analysis_type='hourly',
            avg_consumption=2.0,
            peak_consumption=3.5,
            min_consumption=0.8,
            battery_depletion_rate=5.0,
            projected_runtime=4.5,
            geyser_runtime_available=45.0,
            cost_savings=25.50,
            grid_import_cost=12.75,
            solar_generation_value=38.25
        )
        
        assert analysis.timestamp == timestamp
        assert analysis.analysis_type == 'hourly'
        assert analysis.avg_consumption == 2.0
        assert analysis.cost_savings == 25.50
        
        # Test to_dict method
        data_dict = analysis.to_dict()
        assert 'timestamp' in data_dict
        assert 'analysis_type' in data_dict
        assert data_dict['avg_consumption'] == 2.0


@pytest.mark.asyncio
async def test_global_database_functions():
    """Test global database initialization and cleanup functions."""
    from collector.database import initialize_database, cleanup_database, db_manager
    
    # Mock the database manager
    with patch.object(db_manager, 'connect', new_callable=AsyncMock) as mock_connect:
        with patch.object(db_manager, 'close', new_callable=AsyncMock) as mock_close:
            mock_connect.return_value = True
            
            # Test initialization
            result = await initialize_database()
            assert result is True
            mock_connect.assert_called_once()
            
            # Test cleanup
            await cleanup_database()
            mock_close.assert_called_once()


@pytest.fixture
def sample_solar_metrics():
    """Fixture providing sample solar metrics."""
    return SolarMetrics(
        timestamp=datetime.now(timezone.utc),
        inverter_sn='1029384756',
        plant_id='12345',
        grid_power=0.5,
        battery_power=-0.3,
        solar_power=2.0,
        battery_soc=75.0,
        grid_voltage=235.0,
        battery_voltage=53.5,
        battery_current=-5.6,
        load_power=2.2,
        daily_generation=15.2,
        daily_consumption=12.8,
        hourly_consumption=2.2,
        efficiency=95.0,
        battery_temp=22.5,
        grid_frequency=50.1
    )


@pytest.fixture
def sample_weather_data():
    """Fixture providing sample weather data."""
    return WeatherData(
        timestamp=datetime.now(timezone.utc),
        location='Cape Town,ZA',
        temperature=25.0,
        humidity=65.0,
        cloud_cover=30.0,
        uv_index=8.0,
        sunshine_hours=6.5,
        solar_irradiance=750.0,
        weather_condition='clear',
        wind_speed=5.2,
        pressure=1015.0
    )


def test_data_structures_with_fixtures(sample_solar_metrics, sample_weather_data):
    """Test data structures using fixtures."""
    assert sample_solar_metrics.inverter_sn == '1029384756'
    assert sample_solar_metrics.battery_soc == 75.0
    
    assert sample_weather_data.location == 'Cape Town,ZA'
    assert sample_weather_data.temperature == 25.0
    
    # Test that both structures have valid timestamps
    assert isinstance(sample_solar_metrics.timestamp, datetime)
    assert isinstance(sample_weather_data.timestamp, datetime)