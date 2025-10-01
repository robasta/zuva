#!/usr/bin/env python3
"""
Test script for the consumption analyzer.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add paths for imports
sys.path.append(os.path.dirname(__file__))

from analytics.consumption_analyzer import ConsumptionAnalyzer
from collector.database import DatabaseManager


async def test_analyzer():
    """Test the consumption analyzer."""
    print("🔍 Testing Consumption Analyzer...")
    
    # Create analyzer with mock database
    db_manager = DatabaseManager()
    analyzer = ConsumptionAnalyzer(db_manager)
    
    print(f"✅ Analyzer initialized")
    print(f"   - Battery capacity: {analyzer.battery_capacity_kwh} kWh")
    print(f"   - Inverter capacity: {analyzer.inverter_capacity_kw} kW")
    print(f"   - Geyser power rating: {analyzer.geyser_power_kw} kW")
    print(f"   - Minimum SOC: {analyzer.min_soc}%")
    
    # Test with empty data (no database connection)
    print("\n📊 Testing with empty data...")
    
    hourly_pattern = await analyzer.analyze_hourly_consumption()
    print(f"   - Hourly pattern: {hourly_pattern.period_type}, trend: {hourly_pattern.trend}")
    
    battery_analysis = await analyzer.analyze_battery_usage()
    print(f"   - Battery analysis: SOC {battery_analysis.current_soc}%, runtime {battery_analysis.projected_runtime}h")
    
    energy_flow = await analyzer.analyze_energy_flow()
    print(f"   - Energy flow: Self-consumption {energy_flow.self_consumption_ratio:.1f}%, optimization score {energy_flow.optimization_score:.1f}")
    
    # Test recommendations
    recommendations = await analyzer.generate_optimization_recommendations()
    print(f"   - Recommendations: {len(recommendations)} generated")
    
    # Test internal calculations
    print("\n🧮 Testing internal calculations...")
    
    test_data = [
        {'hour': 9, 'consumption': 2.0},
        {'hour': 9, 'consumption': 2.2},
        {'hour': 10, 'consumption': 1.5},
        {'hour': 11, 'consumption': 3.0}
    ]
    
    averages = analyzer._calculate_hourly_averages(test_data)
    print(f"   - Hourly averages: {averages}")
    
    # Test trend detection
    trend_data = [
        {'timestamp': datetime.now(), 'consumption': 1.0 + i * 0.1}
        for i in range(10)
    ]
    trend = analyzer._detect_trend(trend_data)
    print(f"   - Trend detection: {trend}")
    
    # Test optimization score
    score = analyzer._calculate_optimization_score(85, 75, 15)
    print(f"   - Optimization score: {score:.1f}")
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_analyzer())