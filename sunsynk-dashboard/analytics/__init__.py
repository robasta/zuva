"""
Advanced Analytics Package for Sunsynk Solar Dashboard

Phase 1: Basic consumption analysis and pattern recognition
Phase 2: Machine learning predictions, weather correlation, and intelligent optimization

This package provides comprehensive solar energy management capabilities including:
- Consumption analysis and pattern recognition (Phase 1)
- Battery prediction with ML algorithms (Phase 2)
- Weather correlation analysis (Phase 2)
- Usage optimization and device scheduling (Phase 2)
"""

# Phase 1 Components (Basic Analytics)
from .consumption_analyzer import (
    ConsumptionAnalyzer,
    ConsumptionPattern,
    BatteryAnalysis,
    EnergyFlow
)

# Phase 2 Components (Advanced ML Analytics)
from .battery_predictor import BatteryPredictor, BatteryPrediction, LoadPrediction, SolarPrediction
from .weather_analyzer import WeatherAnalyzer, WeatherCorrelation, SolarForecast
from .usage_optimizer import UsageOptimizer, OptimizationPlan, DeviceSchedule, OptimizationRecommendation

__version__ = "2.0.0"
__all__ = [
    # Phase 1 Components
    'ConsumptionAnalyzer',
    'ConsumptionPattern', 
    'BatteryAnalysis',
    'EnergyFlow',
    # Phase 2 Components
    "BatteryPredictor",
    "BatteryPrediction", 
    "LoadPrediction",
    "SolarPrediction",
    "WeatherAnalyzer",
    "WeatherCorrelation",
    "SolarForecast", 
    "UsageOptimizer",
    "OptimizationPlan",
    "DeviceSchedule",
    "OptimizationRecommendation"
]