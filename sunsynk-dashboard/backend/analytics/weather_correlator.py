"""
Weather Correlation Analyzer - Phase 6 Task 064
Enhanced weather API integration for advanced production correlation analysis
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiohttp
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WeatherForecast:
    """Enhanced weather forecast data structure"""
    timestamp: datetime
    temperature: float
    humidity: float
    cloud_cover: float
    uv_index: float
    solar_radiation: float  # W/m²
    weather_condition: str
    wind_speed: float
    pressure: float
    visibility: float

@dataclass
class SolarProductionCorrelation:
    """Solar production correlation analysis result"""
    correlation_coefficient: float
    prediction_accuracy: float
    optimal_conditions: Dict[str, float]
    efficiency_factors: Dict[str, float]

class AdvancedWeatherAnalyzer:
    """
    Advanced Weather Correlation Analyzer
    Provides detailed weather-solar production correlation analysis
    """
    
    def __init__(self, api_key: str, location: str = None, latitude: float = None, longitude: float = None):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
        # Determine location type and parse accordingly
        if latitude is not None and longitude is not None:
            # Using coordinates
            self.use_coordinates = True
            self.latitude = float(latitude)
            self.longitude = float(longitude)
            self.location = f"{latitude},{longitude}"
        elif location:
            # Using city name
            self.use_coordinates = False
            self.location = location
            self.latitude = None
            self.longitude = None
        else:
            # Default to Randburg, ZA
            self.use_coordinates = False
            self.location = "Randburg,ZA"
            self.latitude = None
            self.longitude = None
        
        # Solar radiation estimation constants
        self.MAX_SOLAR_RADIATION = 1000  # W/m² (peak solar radiation)
        self.PANEL_EFFICIENCY = 0.20  # 20% typical solar panel efficiency
        
    async def get_enhanced_weather_data(self) -> Optional[WeatherForecast]:
        """Get enhanced weather data with solar radiation estimates"""
        try:
            async with aiohttp.ClientSession() as session:
                # Current weather
                current_url = f"{self.base_url}/weather"
                
                # Build parameters based on location type
                if self.use_coordinates:
                    params = {
                        'lat': self.latitude,
                        'lon': self.longitude,
                        'appid': self.api_key,
                        'units': 'metric'
                    }
                else:
                    params = {
                        'q': self.location,
                        'appid': self.api_key,
                        'units': 'metric'
                    }
                
                async with session.get(current_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Weather API error: {response.status}")
                        return None
                        
                    data = await response.json()
                    
                    # Calculate solar radiation estimate
                    cloud_cover = data['clouds']['all']
                    solar_radiation = self._estimate_solar_radiation(
                        cloud_cover, 
                        datetime.now().hour,
                        data['weather'][0]['main'].lower()
                    )
                    
                    return WeatherForecast(
                        timestamp=datetime.now(),
                        temperature=data['main']['temp'],
                        humidity=data['main']['humidity'],
                        cloud_cover=cloud_cover,
                        uv_index=data.get('uvi', 0),  # Not always available
                        solar_radiation=solar_radiation,
                        weather_condition=data['weather'][0]['main'].lower(),
                        wind_speed=data['wind'].get('speed', 0),
                        pressure=data['main']['pressure'],
                        visibility=data.get('visibility', 10000) / 1000  # Convert to km
                    )
                    
        except Exception as e:
            logger.error(f"Enhanced weather data collection error: {e}")
            return None
    
    async def get_weather_forecast(self, days: int = 5) -> List[WeatherForecast]:
        """Get weather forecast for correlation analysis"""
        try:
            async with aiohttp.ClientSession() as session:
                forecast_url = f"{self.base_url}/forecast"
                
                # Build parameters based on location type
                if self.use_coordinates:
                    params = {
                        'lat': self.latitude,
                        'lon': self.longitude,
                        'appid': self.api_key,
                        'units': 'metric'
                    }
                else:
                    params = {
                        'q': self.location,
                        'appid': self.api_key,
                        'units': 'metric'
                    }
                
                async with session.get(forecast_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Forecast API error: {response.status}")
                        return []
                        
                    data = await response.json()
                    forecasts = []
                    
                    for item in data['list'][:days * 8]:  # 3-hour intervals
                        timestamp = datetime.fromtimestamp(item['dt'])
                        cloud_cover = item['clouds']['all']
                        
                        solar_radiation = self._estimate_solar_radiation(
                            cloud_cover,
                            timestamp.hour,
                            item['weather'][0]['main'].lower()
                        )
                        
                        forecast = WeatherForecast(
                            timestamp=timestamp,
                            temperature=item['main']['temp'],
                            humidity=item['main']['humidity'],
                            cloud_cover=cloud_cover,
                            uv_index=0,  # Not available in forecast
                            solar_radiation=solar_radiation,
                            weather_condition=item['weather'][0]['main'].lower(),
                            wind_speed=item['wind'].get('speed', 0),
                            pressure=item['main']['pressure'],
                            visibility=item.get('visibility', 10000) / 1000
                        )
                        forecasts.append(forecast)
                    
                    return forecasts
                    
        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
            return []
    
    def _estimate_solar_radiation(self, cloud_cover: float, hour: int, condition: str) -> float:
        """
        Estimate solar radiation based on weather conditions
        Returns estimated solar radiation in W/m²
        """
        # Base solar radiation by hour (simplified solar curve)
        if 6 <= hour <= 18:
            time_factor = np.sin(np.pi * (hour - 6) / 12)
        else:
            time_factor = 0
            
        base_radiation = self.MAX_SOLAR_RADIATION * time_factor
        
        # Cloud cover reduction factor
        cloud_factor = 1 - (cloud_cover / 100) * 0.8  # 80% max reduction
        
        # Weather condition factors
        condition_factors = {
            'clear': 1.0,
            'clouds': 0.7,
            'rain': 0.3,
            'drizzle': 0.4,
            'thunderstorm': 0.2,
            'snow': 0.1,
            'mist': 0.6,
            'fog': 0.4
        }
        
        condition_factor = condition_factors.get(condition, 0.5)
        
        return max(0, base_radiation * cloud_factor * condition_factor)
    
    def analyze_weather_solar_correlation(self, 
                                        weather_data: List[WeatherForecast],
                                        solar_data: List[Dict]) -> SolarProductionCorrelation:
        """
        Analyze correlation between weather conditions and solar production
        """
        if not weather_data or not solar_data:
            return SolarProductionCorrelation(
                correlation_coefficient=0.0,
                prediction_accuracy=0.0,
                optimal_conditions={},
                efficiency_factors={}
            )
        
        try:
            # Create DataFrame for analysis
            df_weather = pd.DataFrame([{
                'timestamp': w.timestamp,
                'temperature': w.temperature,
                'humidity': w.humidity,
                'cloud_cover': w.cloud_cover,
                'solar_radiation': w.solar_radiation,
                'pressure': w.pressure,
                'wind_speed': w.wind_speed
            } for w in weather_data])
            
            df_solar = pd.DataFrame(solar_data)
            
            # Merge data on timestamp (approximate)
            df_weather['timestamp'] = pd.to_datetime(df_weather['timestamp'])
            df_solar['timestamp'] = pd.to_datetime(df_solar['timestamp'])
            
            # Resample to hourly averages for better correlation
            df_weather_hourly = df_weather.set_index('timestamp').resample('H').mean()
            df_solar_hourly = df_solar.set_index('timestamp').resample('H').mean()
            
            # Merge datasets
            df_merged = df_weather_hourly.join(df_solar_hourly, how='inner')
            
            if len(df_merged) < 5:  # Need minimum data for correlation
                logger.warning("Insufficient data for weather correlation analysis")
                return SolarProductionCorrelation(
                    correlation_coefficient=0.0,
                    prediction_accuracy=0.0,
                    optimal_conditions={},
                    efficiency_factors={}
                )
            
            # Calculate correlations
            solar_power = df_merged['solar_power'].fillna(0)
            
            correlations = {
                'solar_radiation': df_merged['solar_radiation'].corr(solar_power),
                'cloud_cover': df_merged['cloud_cover'].corr(solar_power),
                'temperature': df_merged['temperature'].corr(solar_power),
                'humidity': df_merged['humidity'].corr(solar_power),
                'pressure': df_merged['pressure'].corr(solar_power),
                'wind_speed': df_merged['wind_speed'].corr(solar_power)
            }
            
            # Remove NaN correlations
            correlations = {k: v for k, v in correlations.items() if not pd.isna(v)}
            
            # Overall correlation coefficient (weighted by solar radiation correlation)
            primary_correlation = correlations.get('solar_radiation', 0.0)
            
            # Find optimal conditions (conditions when solar production was highest)
            high_production = df_merged[solar_power > solar_power.quantile(0.75)]
            
            optimal_conditions = {}
            if len(high_production) > 0:
                optimal_conditions = {
                    'temperature': high_production['temperature'].mean(),
                    'humidity': high_production['humidity'].mean(),
                    'cloud_cover': high_production['cloud_cover'].mean(),
                    'pressure': high_production['pressure'].mean(),
                    'wind_speed': high_production['wind_speed'].mean()
                }
            
            # Calculate prediction accuracy (simplified)
            predicted_production = self._predict_solar_production(df_merged)
            actual_production = solar_power
            
            if len(predicted_production) > 0 and len(actual_production) > 0:
                prediction_accuracy = 1 - np.mean(np.abs(predicted_production - actual_production) / (actual_production.max() + 0.001))
                prediction_accuracy = max(0, min(1, prediction_accuracy))
            else:
                prediction_accuracy = 0.0
            
            return SolarProductionCorrelation(
                correlation_coefficient=primary_correlation,
                prediction_accuracy=prediction_accuracy,
                optimal_conditions=optimal_conditions,
                efficiency_factors=correlations
            )
            
        except Exception as e:
            logger.error(f"Weather correlation analysis error: {e}")
            return SolarProductionCorrelation(
                correlation_coefficient=0.0,
                prediction_accuracy=0.0,
                optimal_conditions={},
                efficiency_factors={}
            )
    
    def _predict_solar_production(self, df_merged: pd.DataFrame) -> np.ndarray:
        """Simple solar production prediction based on weather data"""
        try:
            # Simple linear model based on solar radiation and cloud cover
            solar_radiation = df_merged['solar_radiation'].fillna(0)
            cloud_cover = df_merged['cloud_cover'].fillna(50)
            
            # Simplified prediction: production proportional to solar radiation and inversely to cloud cover
            predicted = solar_radiation * (1 - cloud_cover / 100) * self.PANEL_EFFICIENCY / 1000
            
            return predicted.values
            
        except Exception as e:
            logger.error(f"Solar production prediction error: {e}")
            return np.array([])

    def get_production_forecast(self, weather_forecasts: List[WeatherForecast]) -> List[Dict]:
        """
        Generate solar production forecast based on weather predictions
        """
        forecasts = []
        
        for weather in weather_forecasts:
            # Estimate production based on weather conditions
            estimated_radiation = weather.solar_radiation
            cloud_reduction = 1 - (weather.cloud_cover / 100) * 0.8
            
            # Temperature efficiency factor (panels are less efficient when hot)
            temp_efficiency = 1 - max(0, (weather.temperature - 25) * 0.004)  # -0.4% per degree above 25°C
            
            # Estimated production in kW for a 5kW system
            estimated_production = (estimated_radiation / 1000) * 5 * cloud_reduction * temp_efficiency
            
            forecasts.append({
                'timestamp': weather.timestamp,
                'predicted_solar_power': round(max(0, estimated_production), 3),
                'weather_conditions': {
                    'temperature': weather.temperature,
                    'cloud_cover': weather.cloud_cover,
                    'solar_radiation': weather.solar_radiation,
                    'condition': weather.weather_condition
                },
                'confidence': 0.75 if weather.cloud_cover < 50 else 0.60
            })
        
        return forecasts

# Global instance
weather_analyzer = AdvancedWeatherAnalyzer(
    api_key="8c0021a3bea8254c109a414d2efaf9d6",
    location="Randburg,ZA"
)
