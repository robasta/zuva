#!/usr/bin/env python3
"""
Demo runner for Sunsynk Solar Dashboard.
Demonstrates the full system working with mock data.
"""
import asyncio
import sys
import os
import random
import signal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Add paths for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.data_collector import SunsynkDataCollector
from collector.weather_collector import WeatherCollector  
from collector.database import DatabaseManager, SolarMetrics
from analytics.consumption_analyzer import ConsumptionAnalyzer
from analytics.battery_predictor import BatteryPredictor
from analytics.weather_analyzer import WeatherAnalyzer
from analytics.usage_optimizer import UsageOptimizer
from collector.models import EnhancedSolarMetrics, system_health

# Set up environment for demo
os.environ.setdefault('INFLUXDB_TOKEN', 'sunsynk-admin-token')
os.environ.setdefault('INFLUXDB_URL', 'http://localhost:8086')
os.environ.setdefault('INFLUXDB_ORG', 'sunsynk')
os.environ.setdefault('INFLUXDB_BUCKET', 'solar_data')


class DemoDataGenerator:
    """Generate realistic demo solar data."""
    
    def __init__(self):
        self.inverter_sn = "DEMO-123456"
        self.plant_id = "demo-plant-001"
        
    def generate_solar_data(self, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate realistic solar data for demo."""
        if not timestamp:
            timestamp = datetime.now(timezone.utc)
        
        hour = timestamp.hour
        minute = timestamp.minute
        
        # Solar generation pattern (sunrise to sunset)
        if 6 <= hour <= 18:
            # Peak at noon, with some randomness
            solar_factor = max(0, 1 - abs(hour - 12) / 6)
            solar_power = solar_factor * 5.0 + random.uniform(-0.5, 0.5)
        else:
            solar_power = 0.0
        
        # Load pattern (higher in morning and evening)
        if 6 <= hour <= 10 or 17 <= hour <= 22:
            base_load = 2.5
        elif 10 <= hour <= 17:
            base_load = 1.5
        else:
            base_load = 1.0
        
        load_power = base_load + random.uniform(-0.3, 0.3)
        
        # Battery simulation
        battery_soc = max(15, min(100, 50 + (hour - 12) * 3 + random.uniform(-5, 5)))
        
        # Battery power (charging when solar > load, discharging otherwise)
        if solar_power > load_power:
            battery_power = -(solar_power - load_power) * 0.8  # Charging (negative)
        else:
            battery_power = min(3.0, load_power - solar_power)  # Discharging (positive)
        
        # Grid power
        net_power = load_power - solar_power - max(0, battery_power)
        grid_power = max(0, net_power) if net_power > 0 else net_power  # Import positive, export negative
        
        # Battery specs
        battery_voltage = 48.0 + random.uniform(-2, 2)
        battery_current = battery_power / battery_voltage if battery_voltage != 0 else 0
        
        return {
            'timestamp': timestamp,
            'inverter_sn': self.inverter_sn,
            'plant_id': self.plant_id,
            'solar_power': max(0, solar_power),
            'load_power': max(0, load_power),
            'battery_power': battery_power,
            'battery_soc': battery_soc,
            'grid_power': grid_power,
            'battery_voltage': battery_voltage,
            'battery_current': battery_current,
            'grid_voltage': 230.0 + random.uniform(-10, 10),
            'battery_temp': 25.0 + random.uniform(-5, 5),
            'grid_frequency': 50.0 + random.uniform(-0.1, 0.1),
            'daily_generation': hour * 0.8 + random.uniform(0, 2),
            'daily_consumption': hour * 0.6 + random.uniform(0, 1.5)
        }


class DemoRunner:
    """Demo runner for the Sunsynk Solar Dashboard."""
    
    def __init__(self):
        self.running = False
        self.db_manager = DatabaseManager()
        self.analyzer = None
        self.data_generator = DemoDataGenerator()
        self.collection_count = 0
        
    async def start(self):
        """Start the demo runner."""
        print("🚀 Starting Sunsynk Solar Dashboard Demo...")
        
        # Initialize database connection
        if not await self.db_manager.connect():
            print("❌ Failed to connect to database")
            return
        
        print("✅ Connected to InfluxDB")
        
        # Initialize analytics
        # Initialize analytics components
        self.analyzer = ConsumptionAnalyzer(self.db_manager)
        self.battery_predictor = BatteryPredictor(self.db_manager)
        self.weather_analyzer = WeatherAnalyzer(self.db_manager)
        self.usage_optimizer = UsageOptimizer(self.db_manager)
        print("✅ Analytics engine initialized")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        # Generate some historical data first
        await self._generate_historical_data()
        
        # Start real-time demo loop
        await self._demo_loop()
        
    async def _generate_historical_data(self):
        """Generate historical data for analytics."""
        print("📊 Generating historical data for analytics...")
        
        # Generate 24 hours of historical data
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for i in range(288):  # 5-minute intervals for 24 hours
            timestamp = start_time + timedelta(minutes=i * 5)
            data = self.data_generator.generate_solar_data(timestamp)
            
            # Create SolarMetrics object
            solar_metrics = SolarMetrics(
                timestamp=timestamp,
                inverter_sn=data['inverter_sn'],
                plant_id=data['plant_id'],
                grid_power=data['grid_power'],
                battery_power=data['battery_power'],
                solar_power=data['solar_power'],
                battery_soc=data['battery_soc'],
                grid_voltage=data['grid_voltage'],
                battery_voltage=data['battery_voltage'],
                battery_current=data['battery_current'],
                load_power=data['load_power'],
                daily_generation=data['daily_generation'],
                daily_consumption=data['daily_consumption'],
                hourly_consumption=data['load_power'] * (5/60),  # 5-minute consumption in kWh
                efficiency=data['solar_power'] / 5.0 * 100 if data['solar_power'] > 0 else 0,  # % of max capacity
                battery_temp=data['battery_temp'],
                grid_frequency=data['grid_frequency']
            )
            
            await self.db_manager.write_solar_metrics(solar_metrics)
        
        print(f"✅ Generated 288 historical data points")
        
    async def _demo_loop(self):
        """Main demo loop."""
        print("🔄 Starting real-time data collection demo...")
        print("   Press Ctrl+C to stop")
        
        while self.running:
            try:
                # Generate current data
                data = self.data_generator.generate_solar_data()
                
                # Create and store solar metrics
                solar_metrics = SolarMetrics(
                    timestamp=data['timestamp'],
                    inverter_sn=data['inverter_sn'],
                    plant_id=data['plant_id'],
                    grid_power=data['grid_power'],
                    battery_power=data['battery_power'],
                    solar_power=data['solar_power'],
                    battery_soc=data['battery_soc'],
                    grid_voltage=data['grid_voltage'],
                    battery_voltage=data['battery_voltage'],
                    battery_current=data['battery_current'],
                    load_power=data['load_power'],
                    daily_generation=data['daily_generation'],
                    daily_consumption=data['daily_consumption'],
                    hourly_consumption=data['load_power'] * (5/60),  # 5-minute consumption in kWh
                    efficiency=float(data['solar_power'] / 5.0 * 100) if data['solar_power'] > 0 else 0.0,  # % of max capacity
                    battery_temp=data['battery_temp'],
                    grid_frequency=data['grid_frequency']
                )
                
                await self.db_manager.write_solar_metrics(solar_metrics)
                
                self.collection_count += 1
                
                # Display current data
                print(f"📈 Collection #{self.collection_count:3d} | "
                      f"Solar: {data['solar_power']:5.2f}kW | "
                      f"Load: {data['load_power']:5.2f}kW | "
                      f"Battery: {data['battery_soc']:5.1f}% | "
                      f"Grid: {data['grid_power']:+6.2f}kW")
                
                # Run analytics every 30 collections (about 2.5 minutes)
                if self.collection_count % 30 == 0:
                    await self._run_demo_analytics()
                
                # Run Phase 2 advanced analytics every 60 collections (about 5 minutes)
                if self.collection_count % 60 == 0:
                    await self._run_advanced_analytics()
                
                # Sleep for demo interval (5 seconds instead of 30)
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"❌ Error in demo loop: {e}")
                await asyncio.sleep(5)
    
    async def _run_demo_analytics(self):
        """Run analytics for demo."""
        print("\n🧠 Running consumption analytics...")
        
        try:
            # Hourly analysis
            hourly_pattern = await self.analyzer.analyze_hourly_consumption()
            print(f"   📊 Hourly Analysis:")
            print(f"      - Average consumption: {hourly_pattern.avg_consumption:.2f}kW")
            print(f"      - Peak hour: {hourly_pattern.peak_hour}:00")
            print(f"      - Trend: {hourly_pattern.trend}")
            print(f"      - Efficiency score: {hourly_pattern.efficiency_score:.1f}")
            
            # Battery analysis
            battery_analysis = await self.analyzer.analyze_battery_usage()
            print(f"   🔋 Battery Analysis:")
            print(f"      - Current SOC: {battery_analysis.current_soc:.1f}%")
            print(f"      - Projected runtime: {battery_analysis.projected_runtime:.1f}h")
            print(f"      - Geyser opportunities: {len(battery_analysis.geyser_opportunities)}")
            
            # Energy flow
            energy_flow = await self.analyzer.analyze_energy_flow()
            print(f"   ⚡ Energy Flow:")
            print(f"      - Self-consumption: {energy_flow.self_consumption_ratio:.1f}%")
            print(f"      - Grid independence: {energy_flow.grid_independence:.1f}%")
            print(f"      - Optimization score: {energy_flow.optimization_score:.1f}")
            
            # Recommendations
            recommendations = await self.analyzer.generate_optimization_recommendations()
            if recommendations:
                print(f"   💡 Recommendations ({len(recommendations)}):")
                for i, rec in enumerate(recommendations[:3], 1):  # Show top 3
                    print(f"      {i}. [{rec['priority'].upper()}] {rec['title']}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Analytics error: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.db_manager:
            await self.db_manager.close()
        print("✅ Cleanup completed")


async def main():
    """Main entry point."""
    runner = DemoRunner()
    try:
        await runner.start()
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())