"""
Analytics module for Sunsynk Solar Dashboard.
Provides consumption analysis, pattern recognition, and optimization recommendations.
"""

from .consumption_analyzer import (
    ConsumptionAnalyzer,
    ConsumptionPattern,
    BatteryAnalysis,
    EnergyFlow
)

__all__ = [
    'ConsumptionAnalyzer',
    'ConsumptionPattern', 
    'BatteryAnalysis',
    'EnergyFlow'
]