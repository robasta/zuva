"""
Weather data collection service for Sunsynk solar dashboard.
Integrates with OpenWeatherMap API for weather data and solar production correlation.
"""
import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import math

logger = logging.getLogger(__name__)


class WeatherCollector:
    """Weather data collector using OpenWeatherMap API."""
    
    def __init__(self, api_key: str, location: str):
        """Initialize weather collector."""
        self.api_key = api_key
        self.location = location
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.uv_url = "http://api.openweathermap.org/data/2.5/uvi"
        
        # Parse location (city,country_code format)
        location_parts = location.split(',')
        self.city = location_parts[0].strip()
        self.country_code = location_parts[1].strip() if len(location_parts) > 1 else ''
        
        # Cache for reducing API calls
        self._weather_cache = None
        self._cache_time = None
        self._cache_duration = 600  # 10 minutes
        
        logger.info(f"Weather collector initialized for {self.location}")
    
    async def get_current_weather(self) -> Optional[Dict[str, Any]]:
        """Get current weather data with solar correlation metrics."""
        try:
            # Check cache first
            if self._is_cache_valid():
                logger.debug("Using cached weather data")
                return self._weather_cache
            
            async with aiohttp.ClientSession() as session:
                # Get current weather
                weather_data = await self._fetch_current_weather(session)
                if not weather_data:
                    return None
                
                # Get UV index
                uv_data = await self._fetch_uv_index(session, weather_data['coord'])
                
                # Get forecast for sunshine hours calculation
                forecast_data = await self._fetch_forecast(session)
                
                # Combine all data
                combined_data = self._process_weather_data(weather_data, uv_data, forecast_data)
                
                # Cache the result
                self._weather_cache = combined_data
                self._cache_time = datetime.now(timezone.utc)
                
                return combined_data
                
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return None
    
    async def _fetch_current_weather(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Fetch current weather from OpenWeatherMap."""
        try:
            url = f"{self.base_url}/weather"
            params = {
                'q': f"{self.city},{self.country_code}",
                'appid': self.api_key,
                'units': 'metric'
            }
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Current weather fetched for {self.location}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Weather API error {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Weather API request timed out")
            return None
        except Exception as e:
            logger.error(f"Error fetching current weather: {e}")
            return None
    
    async def _fetch_uv_index(self, session: aiohttp.ClientSession, coord: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Fetch UV index data."""
        try:
            params = {
                'lat': coord['lat'],
                'lon': coord['lon'],
                'appid': self.api_key
            }
            
            async with session.get(self.uv_url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug("UV index data fetched")
                    return data
                else:
                    logger.warning(f"UV API error {response.status}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Error fetching UV index: {e}")
            return None
    
    async def _fetch_forecast(self, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Fetch weather forecast for sunshine hours calculation."""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'q': f"{self.city},{self.country_code}",
                'appid': self.api_key,
                'units': 'metric',
                'cnt': 8  # Next 24 hours (3-hour intervals)
            }
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug("Weather forecast fetched")
                    return data
                else:
                    logger.warning(f"Forecast API error {response.status}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Error fetching forecast: {e}")
            return None
    
    def _process_weather_data(
        self, 
        weather: Dict[str, Any], 
        uv_data: Optional[Dict[str, Any]], 
        forecast: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and combine weather data with solar calculations."""
        
        # Basic weather data
        processed_data = {
            'location': self.location,
            'temperature': weather['main']['temp'],
            'humidity': weather['main']['humidity'],
            'pressure': weather['main']['pressure'],
            'cloud_cover': weather['clouds']['all'],
            'weather_condition': weather['weather'][0]['main'].lower(),
            'wind_speed': weather['wind'].get('speed', 0),
            'visibility': weather.get('visibility', 10000) / 1000,  # Convert to km
        }
        
        # UV index
        processed_data['uv_index'] = uv_data.get('value', 0) if uv_data else 0
        
        # Calculate solar irradiance estimate
        processed_data['solar_irradiance'] = self._calculate_solar_irradiance(
            processed_data['cloud_cover'],
            processed_data['uv_index'],
            weather.get('dt', 0)
        )
        
        # Calculate sunshine hours for today
        processed_data['sunshine_hours'] = self._calculate_sunshine_hours(
            forecast,
            weather.get('dt', 0)
        )
        
        # Add derived solar metrics
        processed_data.update(self._calculate_solar_metrics(processed_data))
        
        return processed_data
    
    def _calculate_solar_irradiance(self, cloud_cover: float, uv_index: float, timestamp: int) -> float:
        """Estimate solar irradiance based on cloud cover and UV index."""
        try:
            # Get sun elevation angle
            sun_elevation = self._calculate_sun_elevation(timestamp)
            
            if sun_elevation <= 0:
                return 0.0  # No sun
            
            # Maximum theoretical irradiance at this sun angle
            max_irradiance = 1000 * math.sin(math.radians(sun_elevation))
            
            # Reduce based on cloud cover
            cloud_reduction = 1.0 - (cloud_cover / 100) * 0.8  # Clouds reduce up to 80%
            
            # Adjust based on UV index (normalized to typical maximum of 12)
            uv_factor = min(1.0, uv_index / 8.0)
            
            # Calculate final irradiance
            irradiance = max_irradiance * cloud_reduction * uv_factor
            
            return max(0.0, irradiance)
            
        except Exception as e:
            logger.warning(f"Error calculating solar irradiance: {e}")
            return 0.0
    
    def _calculate_sun_elevation(self, timestamp: int) -> float:
        """Calculate sun elevation angle (simplified calculation)."""
        try:
            # This is a simplified calculation - for production use a proper solar position library
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # Day of year
            day_of_year = dt.timetuple().tm_yday
            
            # Declination angle (simplified)
            declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
            
            # Hour angle (simplified - assumes location at 0° longitude)
            hour_angle = 15 * (dt.hour - 12)
            
            # Assume latitude for Cape Town (-33.9249° S) - this should be configurable
            latitude = -33.9249
            
            # Sun elevation angle
            elevation = math.asin(
                math.sin(math.radians(declination)) * math.sin(math.radians(latitude)) +
                math.cos(math.radians(declination)) * math.cos(math.radians(latitude)) * 
                math.cos(math.radians(hour_angle))
            )
            
            return math.degrees(elevation)
            
        except Exception as e:
            logger.warning(f"Error calculating sun elevation: {e}")
            return 0.0
    
    def _calculate_sunshine_hours(self, forecast: Optional[Dict[str, Any]], current_timestamp: int) -> float:
        """Calculate expected sunshine hours for the rest of the day."""
        try:
            if not forecast or 'list' not in forecast:
                return 0.0
            
            current_dt = datetime.fromtimestamp(current_timestamp, tz=timezone.utc)
            end_of_day = current_dt.replace(hour=18, minute=0, second=0, microsecond=0)
            
            sunshine_hours = 0.0
            
            for item in forecast['list']:
                forecast_dt = datetime.fromtimestamp(item['dt'], tz=timezone.utc)
                
                # Only consider forecasts until end of day
                if forecast_dt > end_of_day:
                    break
                
                # Skip past forecasts
                if forecast_dt <= current_dt:
                    continue
                
                # Calculate sunshine factor based on cloud cover
                cloud_cover = item['clouds']['all']
                sunshine_factor = max(0, 1.0 - (cloud_cover / 100))
                
                # Each forecast item represents 3 hours
                sunshine_hours += sunshine_factor * 3.0
            
            return min(sunshine_hours, 8.0)  # Max 8 hours per day
            
        except Exception as e:
            logger.warning(f"Error calculating sunshine hours: {e}")
            return 0.0
    
    def _calculate_solar_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional solar-related metrics."""
        try:
            cloud_cover = data['cloud_cover']
            uv_index = data['uv_index']
            solar_irradiance = data['solar_irradiance']
            
            # Solar potential (0-100%)
            solar_potential = max(0, 100 - cloud_cover * 0.8)  # Clouds reduce potential
            
            # Generation efficiency factor
            efficiency_factor = min(1.0, solar_irradiance / 800)  # 800 W/m² as good generation threshold
            
            # Weather-based generation forecast
            sunshine_hours = data['sunshine_hours']
            daily_generation_potential = sunshine_hours * efficiency_factor
            
            return {
                'solar_potential': solar_potential,
                'efficiency_factor': efficiency_factor,
                'daily_generation_potential': daily_generation_potential,
                'is_good_solar_day': (
                    cloud_cover < 50 and 
                    solar_irradiance > 300 and 
                    sunshine_hours > 4
                )
            }
            
        except Exception as e:
            logger.warning(f"Error calculating solar metrics: {e}")
            return {}
    
    def _is_cache_valid(self) -> bool:
        """Check if cached weather data is still valid."""
        if not self._weather_cache or not self._cache_time:
            return False
        
        age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return age < self._cache_duration
    
    async def get_hourly_forecast(self) -> List[Dict[str, Any]]:
        """Get hourly weather forecast for the next 24 hours."""
        try:
            async with aiohttp.ClientSession() as session:
                forecast_data = await self._fetch_forecast(session)
                
                if not forecast_data or 'list' not in forecast_data:
                    return []
                
                hourly_forecast = []
                for item in forecast_data['list']:
                    processed_item = {
                        'timestamp': datetime.fromtimestamp(item['dt'], tz=timezone.utc),
                        'temperature': item['main']['temp'],
                        'cloud_cover': item['clouds']['all'],
                        'weather_condition': item['weather'][0]['main'].lower(),
                        'solar_irradiance': self._calculate_solar_irradiance(
                            item['clouds']['all'], 0, item['dt']
                        )
                    }
                    hourly_forecast.append(processed_item)
                
                return hourly_forecast
                
        except Exception as e:
            logger.error(f"Error fetching hourly forecast: {e}")
            return []
    
    async def get_weather_alerts(self) -> List[Dict[str, Any]]:
        """Get weather-based alerts for solar generation."""
        try:
            current_weather = await self.get_current_weather()
            if not current_weather:
                return []
            
            alerts = []
            
            # Low sunshine alert
            if current_weather['sunshine_hours'] < 4:
                alerts.append({
                    'type': 'low_sunshine',
                    'severity': 'warning',
                    'message': f"Low sunshine projected today: {current_weather['sunshine_hours']:.1f} hours",
                    'value': current_weather['sunshine_hours']
                })
            
            # High cloud cover alert
            if current_weather['cloud_cover'] > 80:
                alerts.append({
                    'type': 'high_cloud_cover',
                    'severity': 'info',
                    'message': f"High cloud cover: {current_weather['cloud_cover']}%",
                    'value': current_weather['cloud_cover']
                })
            
            # Low irradiance alert
            if current_weather['solar_irradiance'] < 200:
                alerts.append({
                    'type': 'low_irradiance',
                    'severity': 'warning',
                    'message': f"Low solar irradiance: {current_weather['solar_irradiance']:.0f} W/m²",
                    'value': current_weather['solar_irradiance']
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting weather alerts: {e}")
            return []


# Test function for development
async def test_weather_collector():
    """Test function for the weather collector."""
    import os
    
    api_key = os.getenv('WEATHER_API_KEY')
    if not api_key:
        print("WEATHER_API_KEY not set")
        return
    
    collector = WeatherCollector(api_key, "Cape Town,ZA")
    
    print("Testing current weather...")
    weather = await collector.get_current_weather()
    if weather:
        print(f"Temperature: {weather['temperature']}°C")
        print(f"Cloud cover: {weather['cloud_cover']}%")
        print(f"Solar irradiance: {weather['solar_irradiance']:.0f} W/m²")
        print(f"Sunshine hours: {weather['sunshine_hours']:.1f}h")
        print(f"Good solar day: {weather.get('is_good_solar_day', False)}")
    
    print("\nTesting weather alerts...")
    alerts = await collector.get_weather_alerts()
    for alert in alerts:
        print(f"Alert: {alert['type']} - {alert['message']}")


if __name__ == "__main__":
    asyncio.run(test_weather_collector())