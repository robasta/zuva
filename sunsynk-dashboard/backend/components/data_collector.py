"""
Real Data Collector for Sunsynk Dashboard Phase 6
Handles real-time data collection from Sunsynk inverters
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os
import sys

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
dashboard_dir = os.path.dirname(backend_dir)
root_dir = os.path.dirname(dashboard_dir)
sys.path.extend([root_dir, dashboard_dir, backend_dir])

logger = logging.getLogger(__name__)

class RealDataCollector:
    """Collects real-time data from Sunsynk inverters"""
    
    def __init__(self):
        self.client = None
        self.current_data = None
        self.is_connected = False
        
        # Try to import and initialize Sunsynk client
        try:
            from sunsynk.client import SunsynkClient
            self.SunsynkClient = SunsynkClient
            self._initialize_client()
        except ImportError as e:
            logger.warning(f"⚠️ Sunsynk client not available: {e}")
            self.SunsynkClient = None
    
    def _initialize_client(self):
        """Initialize the Sunsynk client"""
        username = os.getenv('SUNSYNK_USERNAME')
        password = os.getenv('SUNSYNK_PASSWORD')
        
        if username and password:
            try:
                self.client = self.SunsynkClient(username, password)
                logger.info("✅ Sunsynk client initialized")
                self.is_connected = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Sunsynk client: {e}")
                self.is_connected = False
        else:
            logger.warning("⚠️ Sunsynk credentials not provided, using mock data")
            self.is_connected = False
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect current data from the inverter"""
        if not self.is_connected or not self.client:
            return self._generate_mock_data()
        
        try:
            # Use async context manager for proper session handling
            async with self.client as client:
                # Get plants (solar installations)
                plants = await client.get_plants()
                
                if not plants:
                    logger.warning("⚠️ No plants found")
                    return self._generate_mock_data()
                
                # Get the first plant
                plant = plants[0]
                logger.debug(f"📊 Collecting data from plant: {plant.name}")
                
                # Get inverters for the plant
                inverters = await client.get_inverters(plant.id)
                
                if not inverters:
                    logger.warning("⚠️ No inverters found")
                    return self._generate_mock_data()
                
                # Get data from the first inverter
                inverter = inverters[0]
                
                # Collect various data types
                battery_data = await client.get_battery(inverter.serial)
                grid_data = await client.get_grid(inverter.serial)
                input_data = await client.get_input(inverter.serial)
                output_data = await client.get_output(inverter.serial)
                
                # Compile the data
                collected_data = {
                    "timestamp": datetime.now(),
                    "inverter_serial": inverter.serial,
                    "plant_id": plant.id,
                    "plant_name": plant.name,
                    "status": "online",
                    "metrics": {
                        # Battery data
                        "battery_power": battery_data.get_power() if battery_data else 0.0,
                        "battery_voltage": battery_data.get_voltage() if battery_data else 0.0,
                        "battery_current": battery_data.get_current() if battery_data else 0.0,
                        "battery_level": getattr(battery_data, 'soc', 0) if battery_data else 0,
                        
                        # Grid data
                        "grid_power": grid_data.get_power() if grid_data else 0.0,
                        "grid_voltage": grid_data.get_voltage() if grid_data else 0.0,
                        "grid_current": grid_data.get_current() if grid_data else 0.0,
                        "grid_frequency": getattr(grid_data, 'frequency', 50.0) if grid_data else 50.0,
                        
                        # Solar input data
                        "solar_power": input_data.get_power() if input_data else 0.0,
                        "solar_voltage": input_data.get_voltage() if input_data else 0.0,
                        "solar_current": input_data.get_current() if input_data else 0.0,
                        
                        # Output/consumption data
                        "consumption": output_data.get_power() if output_data else 0.0,
                        "output_voltage": output_data.get_voltage() if output_data else 0.0,
                        "output_current": output_data.get_current() if output_data else 0.0,
                        
                        # Calculated fields
                        "grid_consumption": max(0, (output_data.get_power() if output_data else 0) - (input_data.get_power() if input_data else 0)),
                        "inverter_temp": getattr(inverter, 'temperature', 35.0) if hasattr(inverter, 'temperature') else 35.0
                    }
                }
                
                self.current_data = collected_data
                logger.info(f"✅ Successfully collected data from inverter {inverter.serial}")
                return collected_data
                
        except Exception as e:
            logger.error(f"❌ Failed to collect real data: {e}")
            return self._generate_mock_data()
    
    def get_current_data(self) -> Optional[Dict[str, Any]]:
        """Get the most recently collected data"""
        if self.current_data:
            return self.current_data
        else:
            return self._generate_mock_data()
    
    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate mock data when real data is not available"""
        import random
        import math
        
        now = datetime.now()
        hour = now.hour
        
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
        battery_level = 50 + 30 * math.sin(now.minute * 0.1) + random.uniform(-5, 5)
        battery_level = max(10, min(95, battery_level))
        
        mock_data = {
            "timestamp": now,
            "inverter_serial": "2305156257",
            "plant_id": "demo_plant",
            "plant_name": "Demo Solar Installation",
            "status": "mock_data",
            "metrics": {
                "battery_power": round(random.uniform(-2.0, 3.0), 2),
                "battery_voltage": round(48.0 + random.uniform(-2, 2), 1),
                "battery_current": round(random.uniform(-20, 30), 1),
                "battery_level": round(battery_level, 1),
                
                "grid_power": round(max(0, consumption - solar_power), 2),
                "grid_voltage": round(230 + random.uniform(-10, 10), 1),
                "grid_current": round(random.uniform(0, 15), 1),
                "grid_frequency": round(50.0 + random.uniform(-0.1, 0.1), 2),
                
                "solar_power": round(max(0, solar_power), 2),
                "solar_voltage": round(240 + random.uniform(-20, 20), 1),
                "solar_current": round(max(0, solar_power / 48.0), 2),
                
                "consumption": round(consumption, 2),
                "output_voltage": round(230 + random.uniform(-5, 5), 1),
                "output_current": round(consumption / 230.0, 2),
                
                "grid_consumption": round(max(0, consumption - solar_power), 2),
                "inverter_temp": round(35 + random.uniform(-5, 15), 1)
            }
        }
        
        self.current_data = mock_data
        return mock_data
    
    async def start_collection_loop(self, interval_seconds: int = 30):
        """Start continuous data collection loop"""
        logger.info(f"🔄 Starting data collection loop (interval: {interval_seconds}s)")
        
        while True:
            try:
                await self.collect_data()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                logger.info("🛑 Data collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in collection loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    def is_data_fresh(self, max_age_minutes: int = 5) -> bool:
        """Check if current data is fresh enough"""
        if not self.current_data:
            return False
        
        data_age = datetime.now() - self.current_data["timestamp"]
        return data_age.total_seconds() < (max_age_minutes * 60)