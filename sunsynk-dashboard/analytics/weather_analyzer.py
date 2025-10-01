"""
Weather Correlation Analysis Engine for Sunsynk Solar Dashboard.
Analyzes weather impact on solar generation and provides forecasting.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import statistics
import math
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class WeatherCorrelation:
    """Weather correlation analysis results."""
    timestamp: datetime
    correlation_score: float  # -1 to 1
    cloud_impact: float
    temperature_impact: float
    humidity_impact: float
    optimal_conditions: Dict[str, float]
    generation_efficiency: float
    weather_trend: str


@dataclass
class SolarForecast:
    """Solar generation forecast based on weather."""
    timestamp: datetime
    forecast_1h: float
    forecast_4h: float
    forecast_24h: float
    daily_total_kwh: float
    confidence_score: float
    weather_factors: Dict[str, float]
    alerts: List[Dict[str, Any]]


class WeatherAnalyzer:
    """
    Advanced weather correlation analysis for solar generation optimization.
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize weather analyzer."""
        self.db_manager = db_manager or DatabaseManager()
        self.analysis_window_days = 30
        self.min_data_points = 50
        
        # Weather impact factors (learned from data)
        self.impact_weights = {
            'cloud_cover': -0.8,  # Negative impact
            'temperature': 0.3,   # Positive within range
            'humidity': -0.2,     # Slight negative impact
            'wind_speed': 0.1     # Slight positive impact
        }
        
        logger.info("Weather analyzer initialized")
    
    async def analyze_weather_correlation(self) -> WeatherCorrelation:
        """Analyze correlation between weather and solar generation."""
        try:
            # Get historical data
            solar_data = await self.db_manager.get_historical_data(
                'solar_metrics', f'-{self.analysis_window_days}d', None
            )
            weather_data = await self.db_manager.get_historical_data(
                'weather_data', f'-{self.analysis_window_days}d', None
            )
            
            if len(solar_data) < self.min_data_points or len(weather_data) < self.min_data_points:
                return self._create_empty_correlation()
            
            # Match weather and solar data by timestamp
            matched_data = await self._match_weather_solar_data(weather_data, solar_data)
            
            if len(matched_data) < 20:
                return self._create_empty_correlation()
            
            # Calculate correlations
            correlations = await self._calculate_correlations(matched_data)
            
            # Find optimal conditions
            optimal_conditions = await self._find_optimal_conditions(matched_data)
            
            # Calculate generation efficiency
            efficiency = await self._calculate_weather_efficiency(matched_data)
            
            # Determine weather trend
            trend = await self._determine_weather_trend(weather_data)
            
            return WeatherCorrelation(
                timestamp=datetime.now(timezone.utc),
                correlation_score=correlations['overall'],
                cloud_impact=correlations['cloud_cover'],
                temperature_impact=correlations['temperature'],
                humidity_impact=correlations['humidity'],
                optimal_conditions=optimal_conditions,
                generation_efficiency=efficiency,
                weather_trend=trend
            )
            
        except Exception as e:
            logger.error(f"Error in weather correlation analysis: {e}")
            return self._create_empty_correlation()
    
    async def generate_solar_forecast(self, hours_ahead: int = 24) -> SolarForecast:
        """Generate weather-based solar generation forecast."""
        try:
            # Get current weather and forecast
            current_weather = await self._get_current_weather()
            weather_forecast = await self._get_weather_forecast(hours_ahead)
            
            # Get historical patterns
            correlation = await self.analyze_weather_correlation()
            historical_data = await self.db_manager.get_historical_data(
                'solar_metrics', '-7d', None
            )
            
            if not historical_data:
                return self._create_empty_forecast()
            
            # Calculate base solar patterns
            solar_patterns = await self._extract_solar_patterns(historical_data)
            
            # Generate forecasts
            forecast_1h = await self._forecast_solar_generation(
                1, current_weather, solar_patterns, correlation
            )
            forecast_4h = await self._forecast_solar_generation(
                4, weather_forecast, solar_patterns, correlation
            )
            forecast_24h = await self._forecast_solar_generation(
                24, weather_forecast, solar_patterns, correlation
            )
            
            # Calculate daily total
            daily_total = await self._calculate_daily_total_forecast(
                weather_forecast, solar_patterns, correlation
            )
            
            # Calculate confidence
            confidence = await self._calculate_forecast_confidence(
                weather_forecast, correlation, historical_data
            )
            
            # Generate weather alerts
            alerts = await self._generate_weather_alerts(
                weather_forecast, correlation
            )
            
            return SolarForecast(
                timestamp=datetime.now(timezone.utc),
                forecast_1h=forecast_1h,
                forecast_4h=forecast_4h,
                forecast_24h=forecast_24h,
                daily_total_kwh=daily_total,
                confidence_score=confidence,
                weather_factors=current_weather,
                alerts=alerts
            )
            
        except Exception as e:
            logger.error(f"Error generating solar forecast: {e}")
            return self._create_empty_forecast()
    
    async def _match_weather_solar_data(self, weather_data, solar_data):
        """Match weather and solar data by timestamp."""
        matched = []
        
        # Create lookup dict for weather data
        weather_lookup = {}
        for w in weather_data:
            # Round to nearest hour for matching
            hour_key = w['timestamp'].replace(minute=0, second=0, microsecond=0)
            weather_lookup[hour_key] = w
        
        # Match solar data with weather
        for s in solar_data:
            hour_key = s['timestamp'].replace(minute=0, second=0, microsecond=0)
            if hour_key in weather_lookup:
                matched.append({
                    'timestamp': s['timestamp'],
                    'solar_power': s.get('solar_power', 0),
                    'cloud_cover': weather_lookup[hour_key].get('cloud_cover', 0),
                    'temperature': weather_lookup[hour_key].get('temperature', 20),
                    'humidity': weather_lookup[hour_key].get('humidity', 50),
                    'wind_speed': weather_lookup[hour_key].get('wind_speed', 0)
                })
        
        return matched
    
    async def _calculate_correlations(self, matched_data):
        """Calculate weather-solar correlations."""
        if len(matched_data) < 10:
            return {'overall': 0, 'cloud_cover': 0, 'temperature': 0, 'humidity': 0}
        
        solar_values = [d['solar_power'] for d in matched_data]
        cloud_values = [d['cloud_cover'] for d in matched_data]
        temp_values = [d['temperature'] for d in matched_data]
        humidity_values = [d['humidity'] for d in matched_data]
        
        # Simple correlation calculation
        correlations = {
            'cloud_cover': self._calculate_correlation(solar_values, cloud_values),
            'temperature': self._calculate_correlation(solar_values, temp_values),
            'humidity': self._calculate_correlation(solar_values, humidity_values)
        }
        
        # Overall correlation (weighted)
        overall = (
            correlations['cloud_cover'] * abs(self.impact_weights['cloud_cover']) +
            correlations['temperature'] * self.impact_weights['temperature'] +
            correlations['humidity'] * abs(self.impact_weights['humidity'])
        ) / 3
        
        correlations['overall'] = overall
        return correlations
    
    def _calculate_correlation(self, x_values, y_values):
        """Calculate Pearson correlation coefficient."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x_values[i] * y_values[i] for i in range(n))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)
        
        denominator = math.sqrt((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2))
        
        if denominator == 0:
            return 0
        
        correlation = (n * sum_xy - sum_x * sum_y) / denominator
        return max(-1, min(1, correlation))
    
    async def _find_optimal_conditions(self, matched_data):
        """Find optimal weather conditions for solar generation."""
        if not matched_data:
            return {'cloud_cover': 0, 'temperature': 25, 'humidity': 40}
        
        # Find top 25% of solar generation periods
        sorted_data = sorted(matched_data, key=lambda x: x['solar_power'], reverse=True)
        top_quartile = sorted_data[:len(sorted_data)//4] if len(sorted_data) >= 4 else sorted_data
        
        if not top_quartile:
            return {'cloud_cover': 0, 'temperature': 25, 'humidity': 40}
        
        return {
            'cloud_cover': statistics.mean([d['cloud_cover'] for d in top_quartile]),
            'temperature': statistics.mean([d['temperature'] for d in top_quartile]),
            'humidity': statistics.mean([d['humidity'] for d in top_quartile])
        }
    
    async def _calculate_weather_efficiency(self, matched_data):
        """Calculate weather-based generation efficiency."""
        if not matched_data:
            return 0
        
        # Calculate efficiency as actual vs theoretical maximum
        max_possible = max([d['solar_power'] for d in matched_data])
        if max_possible == 0:
            return 0
        
        avg_generation = statistics.mean([d['solar_power'] for d in matched_data])
        return (avg_generation / max_possible) * 100
    
    async def _determine_weather_trend(self, weather_data):
        """Determine weather trend over recent period."""
        if len(weather_data) < 10:
            return 'stable'
        
        # Analyze cloud cover trend
        recent_clouds = [d.get('cloud_cover', 0) for d in weather_data[-24:]]
        older_clouds = [d.get('cloud_cover', 0) for d in weather_data[-48:-24]]
        
        if not recent_clouds or not older_clouds:
            return 'stable'
        
        recent_avg = statistics.mean(recent_clouds)
        older_avg = statistics.mean(older_clouds)
        
        change = recent_avg - older_avg
        
        if change > 10:
            return 'deteriorating'
        elif change < -10:
            return 'improving'
        else:
            return 'stable'
    
    async def _get_current_weather(self):
        """Get current weather conditions."""
        try:
            data = await self.db_manager.get_historical_data(
                'weather_data', '-1h', None
            )
            return data[-1] if data else {}
        except Exception:
            return {}
    
    async def _get_weather_forecast(self, hours_ahead):
        """Get weather forecast (simplified - would use external API)."""
        # Simplified forecast - in production, use weather API
        current_weather = await self._get_current_weather()
        
        if not current_weather:
            return []
        
        forecast = []
        for hour in range(hours_ahead):
            # Simple persistence forecast with slight variation
            forecast_item = {
                'timestamp': datetime.now(timezone.utc) + timedelta(hours=hour),
                'cloud_cover': max(0, min(100, current_weather.get('cloud_cover', 20) + (hour * 2))),
                'temperature': current_weather.get('temperature', 25) + (hour * 0.5),
                'humidity': current_weather.get('humidity', 50)
            }
            forecast.append(forecast_item)
        
        return forecast
    
    async def _extract_solar_patterns(self, historical_data):
        """Extract solar generation patterns by hour."""
        patterns = defaultdict(list)
        
        for record in historical_data:
            hour = record['timestamp'].hour
            solar_power = record.get('solar_power', 0)
            if 6 <= hour <= 18:  # Daylight hours
                patterns[hour].append(solar_power)
        
        # Calculate averages
        avg_patterns = {}
        for hour, values in patterns.items():
            if values:
                avg_patterns[hour] = statistics.mean(values)
        
        return avg_patterns
    
    async def _forecast_solar_generation(self, hours_ahead, weather_data, solar_patterns, correlation):
        """Forecast solar generation for specific time horizon."""
        target_time = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
        target_hour = target_time.hour
        
        # Base generation from patterns
        base_generation = solar_patterns.get(target_hour, 0)
        
        if not weather_data or not isinstance(weather_data, list):
            return base_generation
        
        # Find closest weather forecast
        weather_forecast = weather_data[0] if weather_data else {}
        for w in weather_data:
            if abs((w['timestamp'] - target_time).total_seconds()) < 3600:  # Within 1 hour
                weather_forecast = w
                break
        
        # Apply weather adjustments
        cloud_factor = 1 - (weather_forecast.get('cloud_cover', 0) / 100 * 0.8)
        temp_factor = self._calculate_temperature_factor(weather_forecast.get('temperature', 25))
        
        adjusted_generation = base_generation * cloud_factor * temp_factor
        return max(0, adjusted_generation)
    
    def _calculate_temperature_factor(self, temperature):
        """Calculate temperature impact factor on solar generation."""
        # Optimal temperature range: 15-35°C
        if 15 <= temperature <= 35:
            return 1.0
        elif temperature < 15:
            return max(0.7, 1 - (15 - temperature) / 20)
        else:  # temperature > 35
            return max(0.8, 1 - (temperature - 35) / 25)
    
    async def _calculate_daily_total_forecast(self, weather_forecast, solar_patterns, correlation):
        """Calculate total daily solar generation forecast."""
        if not weather_forecast:
            return 0
        
        total_kwh = 0
        
        for hour in range(6, 19):  # Daylight hours
            base_generation = solar_patterns.get(hour, 0)
            
            # Find weather for this hour
            weather_for_hour = {}
            for w in weather_forecast:
                if w['timestamp'].hour == hour:
                    weather_for_hour = w
                    break
            
            if weather_for_hour:
                cloud_factor = 1 - (weather_for_hour.get('cloud_cover', 0) / 100 * 0.8)
                temp_factor = self._calculate_temperature_factor(
                    weather_for_hour.get('temperature', 25)
                )
                hourly_generation = base_generation * cloud_factor * temp_factor
            else:
                hourly_generation = base_generation
            
            total_kwh += hourly_generation  # Assuming kW readings
        
        return total_kwh
    
    async def _calculate_forecast_confidence(self, weather_forecast, correlation, historical_data):
        """Calculate confidence in the solar forecast."""
        confidence_factors = []
        
        # Weather data availability
        if len(weather_forecast) >= 24:
            confidence_factors.append(0.3)
        elif len(weather_forecast) >= 12:
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.1)
        
        # Historical data quality
        if len(historical_data) >= 168:  # 1 week
            confidence_factors.append(0.3)
        elif len(historical_data) >= 72:  # 3 days
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.1)
        
        # Correlation strength
        correlation_strength = abs(correlation.correlation_score)
        confidence_factors.append(correlation_strength * 0.4)
        
        return min(1.0, sum(confidence_factors))
    
    async def _generate_weather_alerts(self, weather_forecast, correlation):
        """Generate weather-based alerts."""
        alerts = []
        
        if not weather_forecast:
            return alerts
        
        # Check for high cloud cover
        avg_clouds = statistics.mean([w.get('cloud_cover', 0) for w in weather_forecast[:12]])
        if avg_clouds > 70:
            alerts.append({
                'type': 'low_solar_warning',
                'severity': 'medium',
                'message': f'High cloud cover expected: {avg_clouds:.0f}%',
                'recommendation': 'Consider delaying high-power loads'
            })
        
        # Check for extreme temperatures
        max_temp = max([w.get('temperature', 20) for w in weather_forecast[:24]])
        if max_temp > 40:
            alerts.append({
                'type': 'high_temperature_warning',
                'severity': 'low',
                'message': f'High temperature expected: {max_temp:.1f}°C',
                'recommendation': 'Solar efficiency may be reduced'
            })
        
        return alerts
    
    def _create_empty_correlation(self):
        """Create empty weather correlation."""
        return WeatherCorrelation(
            timestamp=datetime.now(timezone.utc),
            correlation_score=0.0,
            cloud_impact=0.0,
            temperature_impact=0.0,
            humidity_impact=0.0,
            optimal_conditions={'cloud_cover': 0, 'temperature': 25, 'humidity': 40},
            generation_efficiency=0.0,
            weather_trend='stable'
        )
    
    def _create_empty_forecast(self):
        """Create empty solar forecast."""
        return SolarForecast(
            timestamp=datetime.now(timezone.utc),
            forecast_1h=0.0,
            forecast_4h=0.0,
            forecast_24h=0.0,
            daily_total_kwh=0.0,
            confidence_score=0.0,
            weather_factors={},
            alerts=[]
        )


# Test function
async def test_weather_analyzer():
    """Test weather analyzer functionality."""
    db_manager = DatabaseManager()
    if not await db_manager.connect():
        print("Could not connect to database")
        return
    
    analyzer = WeatherAnalyzer(db_manager)
    
    print("Testing weather analyzer...")
    
    # Test correlation analysis
    correlation = await analyzer.analyze_weather_correlation()
    print(f"Weather Correlation - Overall: {correlation.correlation_score:.2f}")
    print(f"  Cloud Impact: {correlation.cloud_impact:.2f}")
    print(f"  Temperature Impact: {correlation.temperature_impact:.2f}")
    print(f"  Weather Trend: {correlation.weather_trend}")
    
    # Test solar forecast
    forecast = await analyzer.generate_solar_forecast(24)
    print(f"\nSolar Forecast - Daily Total: {forecast.daily_total_kwh:.2f}kWh")
    print(f"  Confidence: {forecast.confidence_score:.2f}")
    print(f"  Alerts: {len(forecast.alerts)}")
    
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(test_weather_analyzer())
