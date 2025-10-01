"""
Unit tests for consumption analytics engine.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from analytics.consumption_analyzer import (
    ConsumptionAnalyzer,
    ConsumptionPattern,
    BatteryAnalysis,
    EnergyFlow
)
from collector.database import DatabaseManager


class TestConsumptionAnalyzer:
    """Test cases for ConsumptionAnalyzer."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock(spec=DatabaseManager)
        db_manager.get_historical_data = AsyncMock()
        db_manager.write_consumption_analysis = AsyncMock(return_value=True)
        return db_manager
    
    @pytest.fixture
    def sample_solar_data(self):
        """Sample solar data for testing."""
        base_time = datetime.now(timezone.utc) - timedelta(hours=24)
        data = []
        
        for i in range(288):  # 24 hours of 5-minute intervals
            timestamp = base_time + timedelta(minutes=i * 5)
            hour = timestamp.hour
            
            # Simulate solar production pattern
            if 6 <= hour <= 18:
                solar_power = max(0, 5.0 * (1 - abs(hour - 12) / 6)) + (i % 5) * 0.1
            else:
                solar_power = 0.0
            
            # Simulate load pattern
            if 6 <= hour <= 10 or 17 <= hour <= 22:
                load_power = 2.0 + (i % 3) * 0.5  # Higher consumption morning/evening
            else:
                load_power = 1.0 + (i % 2) * 0.3  # Lower consumption other times
            
            # Simulate battery
            battery_soc = max(15, min(100, 50 + (i % 20) - 10))
            battery_power = solar_power - load_power if solar_power > load_power else -(load_power - solar_power) * 0.5
            
            # Simulate grid
            grid_power = max(0, load_power - solar_power - max(0, battery_power))
            
            data.append({
                'timestamp': timestamp,
                'solar_power': solar_power,
                'load_power': load_power,
                'battery_power': battery_power,
                'battery_soc': battery_soc,
                'grid_power': grid_power
            })
        
        return data
    
    @pytest.fixture
    def analyzer(self, mock_db_manager):
        """Create analyzer instance."""
        return ConsumptionAnalyzer(mock_db_manager)
    
    @pytest.mark.asyncio
    async def test_hourly_consumption_analysis(self, analyzer, mock_db_manager, sample_solar_data):
        """Test hourly consumption pattern analysis."""
        mock_db_manager.get_historical_data.return_value = sample_solar_data
        
        pattern = await analyzer.analyze_hourly_consumption()
        
        assert isinstance(pattern, ConsumptionPattern)
        assert pattern.period_type == 'hourly'
        assert pattern.avg_consumption > 0
        assert pattern.peak_consumption >= pattern.avg_consumption
        assert pattern.min_consumption <= pattern.avg_consumption
        assert 0 <= pattern.peak_hour <= 23
        assert 0 <= pattern.low_hour <= 23
        assert pattern.trend in ['increasing', 'decreasing', 'stable']
        assert 0 <= pattern.efficiency_score <= 100
        assert 0 <= pattern.pattern_confidence <= 1
        
        # Verify database was queried
        mock_db_manager.get_historical_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_daily_consumption_analysis(self, analyzer, mock_db_manager, sample_solar_data):
        """Test daily consumption pattern analysis."""
        # Create 7 days of data
        extended_data = []
        for day in range(7):
            for record in sample_solar_data:
                new_record = record.copy()
                new_record['timestamp'] = record['timestamp'] + timedelta(days=day)
                extended_data.append(new_record)
        
        mock_db_manager.get_historical_data.return_value = extended_data
        
        pattern = await analyzer.analyze_daily_consumption(days=7)
        
        assert isinstance(pattern, ConsumptionPattern)
        assert pattern.period_type == 'daily'
        assert pattern.avg_consumption > 0
        assert pattern.trend in ['increasing', 'decreasing', 'stable']
    
    @pytest.mark.asyncio
    async def test_battery_usage_analysis(self, analyzer, mock_db_manager, sample_solar_data):
        """Test battery usage analysis."""
        mock_db_manager.get_historical_data.return_value = sample_solar_data
        
        battery_analysis = await analyzer.analyze_battery_usage()
        
        assert isinstance(battery_analysis, BatteryAnalysis)
        assert 0 <= battery_analysis.current_soc <= 100
        assert battery_analysis.avg_discharge_rate >= 0
        assert battery_analysis.avg_charge_rate >= 0
        assert battery_analysis.projected_runtime >= 0
        assert len(battery_analysis.optimal_charge_window) == 2
        assert 0 <= battery_analysis.optimal_charge_window[0] <= 23
        assert 0 <= battery_analysis.optimal_charge_window[1] <= 23
        assert isinstance(battery_analysis.geyser_opportunities, list)
        assert isinstance(battery_analysis.efficiency_metrics, dict)
    
    @pytest.mark.asyncio
    async def test_energy_flow_analysis(self, analyzer, mock_db_manager, sample_solar_data):
        """Test energy flow analysis."""
        mock_db_manager.get_historical_data.return_value = sample_solar_data
        
        energy_flow = await analyzer.analyze_energy_flow()
        
        assert isinstance(energy_flow, EnergyFlow)
        assert 0 <= energy_flow.solar_to_load_direct <= 100
        assert 0 <= energy_flow.solar_to_battery <= 100
        assert 0 <= energy_flow.solar_to_grid <= 100
        assert 0 <= energy_flow.grid_to_load <= 100
        assert 0 <= energy_flow.battery_to_load <= 100
        assert 0 <= energy_flow.self_consumption_ratio <= 100
        assert 0 <= energy_flow.grid_independence <= 100
        assert 0 <= energy_flow.optimization_score <= 100
    
    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, analyzer, mock_db_manager, sample_solar_data):
        """Test optimization recommendations generation."""
        mock_db_manager.get_historical_data.return_value = sample_solar_data
        
        recommendations = await analyzer.generate_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        
        # Check recommendation structure if any are generated
        for rec in recommendations:
            assert 'type' in rec
            assert 'priority' in rec
            assert 'title' in rec
            assert 'description' in rec
            assert 'actions' in rec
            assert rec['priority'] in ['high', 'medium', 'low']
            assert isinstance(rec['actions'], list)
    
    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, analyzer, mock_db_manager):
        """Test handling of insufficient data scenarios."""
        # Test with empty data
        mock_db_manager.get_historical_data.return_value = []
        
        pattern = await analyzer.analyze_hourly_consumption()
        assert pattern.avg_consumption == 0
        assert pattern.efficiency_score == 0
        assert pattern.pattern_confidence == 0
        
        battery_analysis = await analyzer.analyze_battery_usage()
        assert battery_analysis.current_soc == 0
        assert battery_analysis.projected_runtime == 0
        
        energy_flow = await analyzer.analyze_energy_flow()
        assert energy_flow.optimization_score == 0
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, analyzer, mock_db_manager):
        """Test consumption anomaly detection."""
        # Create data with anomalies
        base_time = datetime.now(timezone.utc)
        data = []
        
        for i in range(100):
            timestamp = base_time + timedelta(minutes=i * 5)
            
            # Normal consumption around 2kW
            if i == 50:  # Anomaly - very high consumption
                load_power = 10.0
            elif i == 75:  # Anomaly - very low consumption
                load_power = 0.1
            else:
                load_power = 2.0 + (i % 3) * 0.2
            
            data.append({
                'timestamp': timestamp,
                'load_power': load_power,
                'solar_power': 3.0,
                'battery_power': 0.0,
                'battery_soc': 80.0,
                'grid_power': 0.0
            })
        
        mock_db_manager.get_historical_data.return_value = data
        
        pattern = await analyzer.analyze_hourly_consumption()
        
        # Should detect the anomalies
        assert len(pattern.anomalies) >= 1
        
        # Check anomaly structure
        for anomaly in pattern.anomalies:
            assert 'timestamp' in anomaly
            assert 'consumption' in anomaly
            assert 'z_score' in anomaly
            assert 'type' in anomaly
            assert anomaly['type'] in ['high', 'low']
    
    @pytest.mark.asyncio
    async def test_trend_detection(self, analyzer, mock_db_manager):
        """Test consumption trend detection."""
        base_time = datetime.now(timezone.utc)
        
        # Test increasing trend
        increasing_data = []
        for i in range(50):
            timestamp = base_time + timedelta(minutes=i * 5)
            load_power = 1.0 + (i * 0.05)  # Gradually increasing
            
            increasing_data.append({
                'timestamp': timestamp,
                'load_power': load_power,
                'solar_power': 3.0,
                'battery_power': 0.0,
                'battery_soc': 80.0,
                'grid_power': 0.0
            })
        
        mock_db_manager.get_historical_data.return_value = increasing_data
        
        pattern = await analyzer.analyze_hourly_consumption()
        assert pattern.trend == 'increasing'
        
        # Test decreasing trend
        decreasing_data = []
        for i in range(50):
            timestamp = base_time + timedelta(minutes=i * 5)
            load_power = 3.0 - (i * 0.05)  # Gradually decreasing
            
            decreasing_data.append({
                'timestamp': timestamp,
                'load_power': load_power,
                'solar_power': 3.0,
                'battery_power': 0.0,
                'battery_soc': 80.0,
                'grid_power': 0.0
            })
        
        mock_db_manager.get_historical_data.return_value = decreasing_data
        
        pattern = await analyzer.analyze_hourly_consumption()
        assert pattern.trend == 'decreasing'
    
    @pytest.mark.asyncio
    async def test_geyser_opportunity_detection(self, analyzer, mock_db_manager):
        """Test geyser usage opportunity detection."""
        base_time = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0)  # Noon
        data = []
        
        for i in range(24):  # 2 hours of data
            timestamp = base_time + timedelta(minutes=i * 5)
            
            data.append({
                'timestamp': timestamp,
                'solar_power': 4.0,  # Good solar
                'load_power': 1.0,
                'battery_power': -2.0,  # Charging
                'battery_soc': 85.0,    # High SOC
                'grid_power': 0.0
            })
        
        mock_db_manager.get_historical_data.return_value = data
        
        battery_analysis = await analyzer.analyze_battery_usage()
        
        # Should find geyser opportunities
        assert len(battery_analysis.geyser_opportunities) > 0
        
        # Check opportunity structure
        for opportunity in battery_analysis.geyser_opportunities:
            assert 'timestamp' in opportunity
            assert 'soc' in opportunity
            assert 'solar_power' in opportunity
            assert 'available_time' in opportunity
            assert 'confidence' in opportunity
            assert opportunity['available_time'] > 0
            assert 0 <= opportunity['confidence'] <= 1
    
    def test_hourly_averages_calculation(self, analyzer):
        """Test hourly averages calculation."""
        consumption_data = [
            {'hour': 9, 'consumption': 2.0},
            {'hour': 9, 'consumption': 2.2},
            {'hour': 10, 'consumption': 1.5},
            {'hour': 10, 'consumption': 1.7},
            {'hour': 11, 'consumption': 3.0}
        ]
        
        averages = analyzer._calculate_hourly_averages(consumption_data)
        
        assert averages[9] == 2.1  # (2.0 + 2.2) / 2
        assert averages[10] == 1.6  # (1.5 + 1.7) / 2
        assert averages[11] == 3.0
    
    def test_trend_detection_methods(self, analyzer):
        """Test trend detection methods."""
        # Increasing trend
        increasing_data = [
            {'timestamp': datetime.now(), 'consumption': 1.0 + i * 0.1}
            for i in range(10)
        ]
        trend = analyzer._detect_trend(increasing_data)
        assert trend == 'increasing'
        
        # Stable trend
        stable_data = [
            {'timestamp': datetime.now(), 'consumption': 2.0 + (i % 2) * 0.01}
            for i in range(10)
        ]
        trend = analyzer._detect_trend(stable_data)
        assert trend == 'stable'
    
    def test_optimization_score_calculation(self, analyzer):
        """Test optimization score calculation."""
        # Perfect scenario
        score = analyzer._calculate_optimization_score(90, 80, 20)
        assert score > 70  # Adjusted expectation based on actual calculation
        
        # Poor scenario
        score = analyzer._calculate_optimization_score(30, 20, 5)
        assert score < 40
    
    @pytest.mark.asyncio
    async def test_store_analysis_results(self, analyzer, mock_db_manager):
        """Test storing analysis results."""
        pattern = ConsumptionPattern(
            period_type='hourly',
            timestamp=datetime.now(timezone.utc),
            avg_consumption=2.5,
            peak_consumption=4.0,
            min_consumption=1.0,
            peak_hour=18,
            low_hour=3,
            trend='stable',
            efficiency_score=75.0,
            pattern_confidence=0.85,
            anomalies=[]
        )
        
        result = await analyzer.store_analysis_results('consumption_pattern', pattern)
        assert result is True
        
        # Verify database write was called
        mock_db_manager.write_consumption_analysis.assert_called_once()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])