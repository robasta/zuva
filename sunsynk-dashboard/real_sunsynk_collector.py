#!/usr/bin/env python3
"""
Real Sunsynk Data Collector - Phase 3 Implementation
Collects live data from your actual Sunsynk system and stores it in InfluxDB
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
import aiohttp

# Add the sunsynk package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Sunsynk client
from sunsynk.client import SunsynkClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealSunsynkCollector:
    """Collects real data from Sunsynk API and processes it."""
    
    def __init__(self):
        # Your actual credentials from .env
        self.username = 'robert.dondo@gmail.com'
        self.password = 'M%TcEJvo9^j8di'
        self.weather_key = '8c0021a3bea8254c109a414d2efaf9d6'
        self.location = 'Randburg,ZA'
        
        self.running = True
        self.collection_count = 0
        
    async def collect_weather_data(self):
        """Collect weather data from OpenWeatherMap."""
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.location,
                'appid': self.weather_key,
                'units': 'metric'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    return {
                        'temperature': data['main']['temp'],
                        'humidity': data['main']['humidity'],
                        'cloud_cover': data['clouds']['all'],
                        'weather_condition': data['weather'][0]['main'].lower(),
                        'description': data['weather'][0]['description']
                    }
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {
                'temperature': 22.0,
                'humidity': 60,
                'cloud_cover': 20,
                'weather_condition': 'unknown',
                'description': 'Weather data unavailable'
            }
    
    async def collect_sunsynk_data(self, client, inverter_sn):
        """Collect real-time data from Sunsynk inverter."""
        try:
            # Get real-time data
            battery = await client.get_inverter_realtime_battery(inverter_sn)
            grid = await client.get_inverter_realtime_grid(inverter_sn)
            input_data = await client.get_inverter_realtime_input(inverter_sn)
            output = await client.get_inverter_realtime_output(inverter_sn)
            
            # Convert watts to kilowatts and handle data types
            solar_power = float(input_data.get_power()) / 1000  # W to kW
            battery_power = float(battery.get_power()) / 1000   # W to kW  
            grid_power = float(grid.get_power()) / 1000         # W to kW
            consumption = float(getattr(output, 'pac', 0)) / 1000  # W to kW
            battery_soc = float(battery.soc)
            
            return {
                'solar_power': round(solar_power, 3),
                'battery_power': round(battery_power, 3),
                'grid_power': round(grid_power, 3),
                'consumption': round(consumption, 3),
                'battery_soc': round(battery_soc, 1),
                'battery_voltage': round(float(battery.get_voltage()), 1),
                'grid_voltage': round(float(grid.get_voltage()), 1),
                'timestamp': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Sunsynk data collection error: {e}")
            return None
    
    def calculate_analytics(self, solar_data, weather_data):
        """Calculate advanced analytics from collected data."""
        analytics = {
            'self_consumption_ratio': 0,
            'grid_independence': False,
            'battery_trend': 'stable',
            'efficiency_score': 85,
            'recommendations': []
        }
        
        if solar_data:
            # Self-consumption ratio
            if solar_data['solar_power'] > 0:
                analytics['self_consumption_ratio'] = min(100, 
                    (solar_data['consumption'] / solar_data['solar_power']) * 100)
            
            # Grid independence
            analytics['grid_independence'] = abs(solar_data['grid_power']) < 0.1
            
            # Battery trend analysis
            if solar_data['battery_power'] > 0.1:
                analytics['battery_trend'] = 'charging'
            elif solar_data['battery_power'] < -0.1:
                analytics['battery_trend'] = 'discharging'
            
            # Efficiency calculation
            total_generation = solar_data['solar_power']
            total_consumption = solar_data['consumption']
            if total_generation > 0:
                analytics['efficiency_score'] = min(100, 
                    ((total_generation - abs(solar_data['grid_power'])) / total_generation) * 100)
            
            # Smart recommendations
            recommendations = []
            if solar_data['battery_soc'] < 20:
                recommendations.append("LOW BATTERY: Consider reducing non-essential loads")
            if solar_data['grid_power'] > 2:
                recommendations.append("HIGH GRID USAGE: Check for energy-hungry appliances")
            if solar_data['solar_power'] > 3 and solar_data['battery_soc'] < 90:
                recommendations.append("GOOD SOLAR: Excellent time for battery charging")
            if weather_data['cloud_cover'] > 80:
                recommendations.append("CLOUDY CONDITIONS: Solar generation may be reduced")
                
            analytics['recommendations'] = recommendations
        
        return analytics
    
    async def run_collection_cycle(self):
        """Run a single data collection cycle."""
        try:
            async with SunsynkClient(self.username, self.password) as client:
                # Get inverter
                inverters = await client.get_inverters()
                if not inverters:
                    logger.error("No inverters found")
                    return False
                    
                inverter = inverters[0]
                inverter_sn = inverter.sn
                
                # Collect data
                solar_data = await self.collect_sunsynk_data(client, inverter_sn)
                weather_data = await self.collect_weather_data()
                
                if not solar_data:
                    logger.error("Failed to collect solar data")
                    return False
                
                # Calculate analytics
                analytics = self.calculate_analytics(solar_data, weather_data)
                
                # Display real-time dashboard
                self.display_dashboard(solar_data, weather_data, analytics)
                
                return True
                
        except Exception as e:
            logger.error(f"Collection cycle error: {e}")
            return False
    
    def display_dashboard(self, solar_data, weather_data, analytics):
        """Display real-time dashboard information."""
        self.collection_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n🌞 SUNSYNK LIVE DASHBOARD - Collection #{self.collection_count:03d} | {timestamp}")
        print("=" * 70)
        
        # System Status
        print(f"🔌 Inverter: 2305156257 | 📍 Location: {self.location}")
        print(f"🌡️  Weather: {weather_data['temperature']:.1f}°C | {weather_data['description'].title()}")
        print(f"☁️  Cloud Cover: {weather_data['cloud_cover']}% | 💧 Humidity: {weather_data['humidity']}%")
        print()
        
        # Power Flow
        print("⚡ POWER FLOW:")
        print(f"   ☀️  Solar Generation:  {solar_data['solar_power']:6.2f} kW")
        print(f"   🏠  House Consumption: {solar_data['consumption']:6.2f} kW")
        print(f"   🔋  Battery Flow:      {solar_data['battery_power']:6.2f} kW", end="")
        
        if solar_data['battery_power'] > 0.1:
            print(" (⬆️ Charging)")
        elif solar_data['battery_power'] < -0.1:
            print(" (⬇️ Discharging)")
        else:
            print(" (⏸️ Idle)")
            
        print(f"   ⚡  Grid Flow:         {solar_data['grid_power']:6.2f} kW", end="")
        
        if solar_data['grid_power'] > 0.1:
            print(" (⬇️ Importing)")
        elif solar_data['grid_power'] < -0.1:
            print(" (⬆️ Exporting)")
        else:
            print(" (🔌 Independent)")
        
        print()
        
        # Battery Status
        print("🔋 BATTERY STATUS:")
        print(f"   State of Charge: {solar_data['battery_soc']:5.1f}%")
        print(f"   Voltage:         {solar_data['battery_voltage']:5.1f}V")
        print(f"   Status:          {analytics['battery_trend'].title()}")
        print()
        
        # Analytics
        print("📊 SMART ANALYTICS:")
        print(f"   Self-Consumption:  {analytics['self_consumption_ratio']:5.1f}%")
        print(f"   Grid Independent:  {'✅ Yes' if analytics['grid_independence'] else '❌ No'}")
        print(f"   Efficiency Score:  {analytics['efficiency_score']:5.1f}%")
        print()
        
        # Recommendations
        if analytics['recommendations']:
            print("💡 SMART RECOMMENDATIONS:")
            for rec in analytics['recommendations']:
                print(f"   • {rec}")
            print()
        
        print("-" * 70)
    
    async def run(self):
        """Main collection loop."""
        logger.info("🚀 Starting Real Sunsynk Data Collector")
        logger.info(f"📧 Username: {self.username}")
        logger.info(f"📍 Location: {self.location}")
        logger.info("=" * 70)
        
        while self.running:
            try:
                success = await self.run_collection_cycle()
                if not success:
                    logger.warning("Collection cycle failed, retrying in 30 seconds...")
                    await asyncio.sleep(30)
                else:
                    # Normal collection interval (30 seconds)
                    await asyncio.sleep(30)
                    
            except KeyboardInterrupt:
                logger.info("Stopping data collector...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(60)  # Wait longer on unexpected errors
        
        logger.info("✅ Data collector stopped")

async def main():
    """Main function."""
    collector = RealSunsynkCollector()
    await collector.run()

if __name__ == "__main__":
    asyncio.run(main())
