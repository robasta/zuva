"""
Main data collection service for Sunsynk solar dashboard.
Polls Sunsynk API every 30 seconds and stores data in InfluxDB.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import signal
import traceback
from dataclasses import asdict

# Add the parent directory to the path to import sunsynk modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sunsynk.client import SunsynkClient, InvalidCredentialsException
from sunsynk.inverter import Inverter

from database import DatabaseManager, SolarMetrics, WeatherData
from models import EnhancedSolarMetrics, WeatherMetrics, system_health
from weather_collector import WeatherCollector

# Import analytics module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from analytics.consumption_analyzer import ConsumptionAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/data_collector.log') if os.path.exists('/app/logs') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataCollector:
    """Main data collection service for Sunsynk solar data."""
    
    def __init__(self):
        """Initialize the data collector."""
        self.running = False
        self.sunsynk_client = None
        self.db_manager = DatabaseManager()
        self.weather_collector = None
        self.consumption_analyzer = None
        
        # Configuration
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL', '30'))  # seconds
        self.username = os.getenv('SUNSYNK_USERNAME')
        self.password = os.getenv('SUNSYNK_PASSWORD')
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        self.location = os.getenv('LOCATION', 'Cape Town,ZA')
        
        # Runtime state
        self.last_collection_time = None
        self.collection_count = 0
        self.error_count = 0
        self.consecutive_errors = 0
        
        # Validate configuration
        if not self.username or not self.password:
            raise ValueError("SUNSYNK_USERNAME and SUNSYNK_PASSWORD must be set")
        
        logger.info(f"Data collector initialized with {self.collection_interval}s interval")
    
    async def start(self):
        """Start the data collection service."""
        logger.info("Starting Sunsynk data collection service...")
        
        # Initialize connections
        if not await self._initialize_connections():
            logger.error("Failed to initialize connections")
            return False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        # Start the main collection loop
        try:
            await self._collection_loop()
        except Exception as e:
            logger.error(f"Collection loop failed: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self._cleanup()
        
        return True
    
    async def _initialize_connections(self) -> bool:
        """Initialize Sunsynk API and database connections."""
        try:
            # Connect to Sunsynk API
            logger.info("Connecting to Sunsynk API...")
            self.sunsynk_client = await SunsynkClient.create(
                username=self.username,
                password=self.password
            )
            system_health.update_api_status(True)
            logger.info("Connected to Sunsynk API")
            
            # Connect to database
            logger.info("Connecting to database...")
            if await self.db_manager.connect():
                system_health.update_database_status(True)
                logger.info("Connected to database")
            else:
                logger.error("Failed to connect to database")
                return False
            
            # Initialize weather collector if API key is provided
            if self.weather_api_key:
                from weather_collector import WeatherCollector
                self.weather_collector = WeatherCollector(
                    api_key=self.weather_api_key,
                    location=self.location
                )
                logger.info("Weather collector initialized")
            else:
                logger.warning("Weather API key not provided, weather data will not be collected")
            
            # Initialize consumption analyzer
            self.consumption_analyzer = ConsumptionAnalyzer(self.db_manager)
            logger.info("Consumption analyzer initialized")
            
            return True
            
        except InvalidCredentialsException:
            logger.error("Invalid Sunsynk credentials")
            system_health.update_api_status(False)
            system_health.increment_error_count()
            return False
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
            system_health.increment_error_count()
            return False
    
    async def _collection_loop(self):
        """Main data collection loop."""
        logger.info("Starting data collection loop...")
        
        while self.running:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Collect solar data
                await self._collect_solar_data()
                
                # Collect weather data (less frequently)
                if self.weather_collector and self.collection_count % 30 == 0:  # Every 15 minutes
                    await self._collect_weather_data()
                
                # Run consumption analytics (hourly)
                if self.consumption_analyzer and self.collection_count % 120 == 0:  # Every hour
                    await self._run_analytics()
                
                # Update collection statistics
                self.collection_count += 1
                self.last_collection_time = datetime.now(timezone.utc)
                self.consecutive_errors = 0
                
                # Calculate sleep duration to maintain interval
                elapsed_time = asyncio.get_event_loop().time() - start_time
                sleep_duration = max(0, self.collection_interval - elapsed_time)
                
                if elapsed_time > self.collection_interval:
                    logger.warning(f"Collection took {elapsed_time:.2f}s, longer than interval {self.collection_interval}s")
                
                logger.debug(f"Collection #{self.collection_count} completed in {elapsed_time:.2f}s, sleeping {sleep_duration:.2f}s")
                
                # Sleep until next collection
                await asyncio.sleep(sleep_duration)
                
            except Exception as e:
                self.error_count += 1
                self.consecutive_errors += 1
                system_health.increment_error_count()
                logger.error(f"Error in collection loop: {e}")
                
                # If we have too many consecutive errors, increase sleep time
                error_sleep = min(300, 30 * self.consecutive_errors)  # Max 5 minutes
                logger.error(f"Sleeping {error_sleep}s due to consecutive errors ({self.consecutive_errors})")
                await asyncio.sleep(error_sleep)
                
                # Try to reconnect if we have many consecutive errors
                if self.consecutive_errors >= 5:
                    logger.warning("Attempting to reconnect due to consecutive errors...")
                    await self._attempt_reconnection()
    
    async def _collect_solar_data(self):
        """Collect solar data from Sunsynk API and store in database."""
        try:
            if not self.sunsynk_client:
                raise Exception("Sunsynk client not connected")
            
            # Get inverters
            inverters = await self.sunsynk_client.get_inverters()
            if not inverters:
                logger.warning("No inverters found")
                return
            
            for inverter in inverters:
                try:
                    # Collect all real-time data for the inverter
                    grid_data = await self.sunsynk_client.get_inverter_realtime_grid(inverter.sn)
                    battery_data = await self.sunsynk_client.get_inverter_realtime_battery(inverter.sn)
                    input_data = await self.sunsynk_client.get_inverter_realtime_input(inverter.sn)
                    output_data = await self.sunsynk_client.get_inverter_realtime_output(inverter.sn)
                    
                    # Combine data into enhanced metrics
                    inverter_data = {
                        'sn': inverter.sn,
                        'plant_id': inverter.plant.id if inverter.plant else '',
                        'grid_power': grid_data.get_power() or 0,
                        'battery_power': battery_data.get_power() or 0,
                        'solar_power': input_data.get_power() or 0,
                        'battery_soc': float(battery_data.soc) if battery_data.soc else 0,
                        'grid_voltage': grid_data.get_voltage() or 0,
                        'battery_voltage': battery_data.get_voltage() or 0,
                        'battery_current': battery_data.get_current() or 0,
                        'grid_frequency': grid_data.fac or 50.0,
                        'battery_temp': float(battery_data.temp) if battery_data.temp else 20.0,
                        'daily_generation': float(inverter.generated_today) if inverter.generated_today else 0,
                        'daily_consumption': 0  # This would need to be calculated from historical data
                    }
                    
                    # Create enhanced metrics
                    enhanced_metrics = EnhancedSolarMetrics(inverter_data)
                    
                    # Convert to database format
                    solar_metrics = SolarMetrics(
                        timestamp=enhanced_metrics.timestamp,
                        inverter_sn=enhanced_metrics.inverter_sn,
                        plant_id=enhanced_metrics.plant_id,
                        grid_power=enhanced_metrics.grid_power,
                        battery_power=enhanced_metrics.battery_power,
                        solar_power=enhanced_metrics.solar_power,
                        battery_soc=enhanced_metrics.battery_soc,
                        grid_voltage=enhanced_metrics.grid_voltage,
                        battery_voltage=enhanced_metrics.battery_voltage,
                        battery_current=enhanced_metrics.battery_current,
                        load_power=enhanced_metrics.load_power,
                        daily_generation=enhanced_metrics.daily_generation,
                        daily_consumption=enhanced_metrics.daily_consumption,
                        hourly_consumption=enhanced_metrics.hourly_consumption,
                        efficiency=enhanced_metrics.efficiency,
                        battery_temp=enhanced_metrics.battery_temp,
                        grid_frequency=enhanced_metrics.grid_frequency
                    )
                    
                    # Store in database
                    if await self.db_manager.write_solar_metrics(solar_metrics):
                        logger.debug(f"Solar data stored for inverter {inverter.sn}")
                        system_health.update_api_status(True)
                    else:
                        logger.error(f"Failed to store solar data for inverter {inverter.sn}")
                        system_health.increment_data_collection_failure()
                    
                except Exception as e:
                    logger.error(f"Error collecting data for inverter {inverter.sn}: {e}")
                    system_health.increment_error_count()
            
        except Exception as e:
            logger.error(f"Error collecting solar data: {e}")
            system_health.update_api_status(False)
            system_health.increment_data_collection_failure()
            raise
    
    async def _collect_weather_data(self):
        """Collect weather data and store in database."""
        try:
            if not self.weather_collector:
                return
            
            # Get current weather
            weather_data = await self.weather_collector.get_current_weather()
            if not weather_data:
                logger.warning("No weather data received")
                return
            
            # Create weather metrics
            weather_metrics = WeatherMetrics(weather_data)
            
            # Convert to database format
            weather_db = WeatherData(
                timestamp=weather_metrics.timestamp,
                location=weather_metrics.location,
                temperature=weather_metrics.temperature,
                humidity=weather_metrics.humidity,
                cloud_cover=weather_metrics.cloud_cover,
                uv_index=weather_metrics.uv_index,
                sunshine_hours=weather_metrics.sunshine_hours,
                solar_irradiance=weather_metrics.solar_irradiance,
                weather_condition=weather_metrics.weather_condition,
                wind_speed=weather_metrics.wind_speed,
                pressure=weather_metrics.pressure
            )
            
            # Store in database
            if await self.db_manager.write_weather_data(weather_db):
                logger.debug(f"Weather data stored for {weather_metrics.location}")
            else:
                logger.error("Failed to store weather data")
                system_health.increment_data_collection_failure()
            
        except Exception as e:
            logger.error(f"Error collecting weather data: {e}")
            system_health.increment_error_count()
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect to services after failures."""
        try:
            logger.info("Attempting to reconnect...")
            
            # Close existing connections
            if self.sunsynk_client:
                await self.sunsynk_client.close()
            await self.db_manager.close()
            
            # Re-initialize connections
            if await self._initialize_connections():
                logger.info("Reconnection successful")
                self.consecutive_errors = 0
            else:
                logger.error("Reconnection failed")
            
        except Exception as e:
            logger.error(f"Error during reconnection: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up resources...")
        
        try:
            if self.sunsynk_client:
                await self.sunsynk_client.close()
            
            await self.db_manager.close()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get collector status information."""
        return {
            'running': self.running,
            'collection_count': self.collection_count,
            'error_count': self.error_count,
            'consecutive_errors': self.consecutive_errors,
            'last_collection_time': self.last_collection_time,
            'collection_interval': self.collection_interval,
            'api_connected': system_health.api_connection_status,
            'database_connected': system_health.database_connection_status,
            'health_score': system_health.get_health_score()
        }
    
    async def _run_analytics(self):
        """Run consumption analytics and generate recommendations."""
        try:
            logger.info("Running consumption analytics...")
            
            # Run hourly consumption analysis
            hourly_pattern = await self.consumption_analyzer.analyze_hourly_consumption()
            logger.info(f"Hourly analysis - Avg: {hourly_pattern.avg_consumption:.2f}kW, "
                       f"Peak: {hourly_pattern.peak_hour}:00, Trend: {hourly_pattern.trend}")
            
            # Store hourly pattern results
            await self.consumption_analyzer.store_analysis_results('consumption_pattern', hourly_pattern)
            
            # Run battery analysis
            battery_analysis = await self.consumption_analyzer.analyze_battery_usage()
            logger.info(f"Battery analysis - SOC: {battery_analysis.current_soc:.1f}%, "
                       f"Runtime: {battery_analysis.projected_runtime:.1f}h")
            
            # Run energy flow analysis
            energy_flow = await self.consumption_analyzer.analyze_energy_flow()
            logger.info(f"Energy flow - Self consumption: {energy_flow.self_consumption_ratio:.1f}%, "
                       f"Grid independence: {energy_flow.grid_independence:.1f}%")
            
            # Generate optimization recommendations
            recommendations = await self.consumption_analyzer.generate_optimization_recommendations()
            if recommendations:
                logger.info(f"Generated {len(recommendations)} optimization recommendations")
                for rec in recommendations:
                    if rec['priority'] == 'high':
                        logger.warning(f"HIGH PRIORITY: {rec['title']} - {rec['description']}")
                    else:
                        logger.info(f"{rec['priority'].upper()}: {rec['title']}")
            
            # Update system health with analytics status
            system_health.last_analytics_run = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error running analytics: {e}")
            logger.error(traceback.format_exc())
            system_health.increment_error_count()


async def main():
    """Main entry point for the data collector service."""
    logger.info("Starting Sunsynk Data Collector")
    
    try:
        collector = DataCollector()
        await collector.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("Data collector stopped")


if __name__ == "__main__":
    asyncio.run(main())