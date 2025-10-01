"""
Consumption Analytics Engine for Sunsynk Solar Dashboard.
Provides hourly, daily, and monthly consumption analysis with pattern recognition.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import statistics
from dataclasses import dataclass, asdict
import math

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.database import DatabaseManager, ConsumptionAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ConsumptionPattern:
    """Represents a consumption pattern analysis."""
    period_type: str  # hourly, daily, weekly, monthly
    timestamp: datetime
    avg_consumption: float
    peak_consumption: float
    min_consumption: float
    peak_hour: int
    low_hour: int
    trend: str  # increasing, decreasing, stable
    efficiency_score: float
    pattern_confidence: float  # 0-1 score for pattern reliability
    anomalies: List[Dict[str, Any]]


@dataclass
class BatteryAnalysis:
    """Battery usage and optimization analysis."""
    timestamp: datetime
    current_soc: float
    avg_discharge_rate: float  # %/hour
    avg_charge_rate: float     # %/hour
    projected_runtime: float   # hours until min SOC
    optimal_charge_window: Tuple[int, int]  # (start_hour, end_hour)
    geyser_opportunities: List[Dict[str, Any]]
    efficiency_metrics: Dict[str, float]


@dataclass
class EnergyFlow:
    """Energy flow analysis and optimization."""
    timestamp: datetime
    solar_to_load_direct: float    # %
    solar_to_battery: float        # %
    solar_to_grid: float           # %
    grid_to_load: float            # %
    battery_to_load: float         # %
    self_consumption_ratio: float   # %
    grid_independence: float        # %
    optimization_score: float      # 0-100


class ConsumptionAnalyzer:
    """
    Advanced consumption analytics engine with pattern recognition
    and optimization recommendations.
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize consumption analyzer."""
        self.db_manager = db_manager or DatabaseManager()
        self.analysis_window_hours = 24
        self.min_data_points = 10
        
        # Configuration from environment
        self.battery_capacity_kwh = float(os.getenv('BATTERY_CAPACITY_KWH', '5.0'))
        self.inverter_capacity_kw = float(os.getenv('INVERTER_CAPACITY_KW', '5.0'))
        self.geyser_power_kw = float(os.getenv('GEYSER_POWER_RATING', '3.0'))
        self.min_soc = float(os.getenv('BATTERY_MIN_SOC', '15.0'))
        
        # Analysis cache
        self._analysis_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("Consumption analyzer initialized")
    
    async def analyze_hourly_consumption(
        self, 
        start_time: datetime = None,
        hours: int = 24
    ) -> ConsumptionPattern:
        """Analyze hourly consumption patterns."""
        try:
            if not start_time:
                start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get historical data
            data = await self.db_manager.get_historical_data(
                'solar_metrics',
                f'-{hours}h',
                None
            )
            
            if len(data) < self.min_data_points:
                logger.warning(f"Insufficient data for hourly analysis: {len(data)} points")
                return self._create_empty_pattern('hourly')
            
            # Extract consumption values and timestamps
            consumption_data = []
            for record in data:
                if record.get('load_power') is not None:
                    consumption_data.append({
                        'timestamp': record['timestamp'],
                        'consumption': float(record['load_power']),
                        'hour': record['timestamp'].hour
                    })
            
            if not consumption_data:
                return self._create_empty_pattern('hourly')
            
            # Calculate statistics
            consumptions = [d['consumption'] for d in consumption_data]
            avg_consumption = statistics.mean(consumptions)
            peak_consumption = max(consumptions)
            min_consumption = min(consumptions)
            
            # Find peak and low hours
            hourly_averages = self._calculate_hourly_averages(consumption_data)
            peak_hour = max(hourly_averages.keys(), key=lambda h: hourly_averages[h])
            low_hour = min(hourly_averages.keys(), key=lambda h: hourly_averages[h])
            
            # Detect trend
            trend = self._detect_trend(consumption_data)
            
            # Calculate efficiency score
            efficiency_score = self._calculate_efficiency_score(consumption_data, data)
            
            # Detect anomalies
            anomalies = self._detect_consumption_anomalies(consumption_data)
            
            # Calculate pattern confidence
            pattern_confidence = self._calculate_pattern_confidence(consumption_data)
            
            return ConsumptionPattern(
                period_type='hourly',
                timestamp=datetime.now(timezone.utc),
                avg_consumption=avg_consumption,
                peak_consumption=peak_consumption,
                min_consumption=min_consumption,
                peak_hour=peak_hour,
                low_hour=low_hour,
                trend=trend,
                efficiency_score=efficiency_score,
                pattern_confidence=pattern_confidence,
                anomalies=anomalies
            )
            
        except Exception as e:
            logger.error(f"Error in hourly consumption analysis: {e}")
            return self._create_empty_pattern('hourly')
    
    async def analyze_daily_consumption(self, days: int = 7) -> ConsumptionPattern:
        """Analyze daily consumption patterns."""
        try:
            # Get data for the specified number of days
            data = await self.db_manager.get_historical_data(
                'solar_metrics',
                f'-{days}d',
                None
            )
            
            if len(data) < self.min_data_points:
                logger.warning(f"Insufficient data for daily analysis: {len(data)} points")
                return self._create_empty_pattern('daily')
            
            # Group data by day
            daily_data = self._group_data_by_day(data)
            
            if len(daily_data) < 2:
                logger.warning("Need at least 2 days of data for daily analysis")
                return self._create_empty_pattern('daily')
            
            # Calculate daily consumption totals
            daily_consumptions = []
            for day, day_data in daily_data.items():
                total_consumption = sum(
                    record.get('load_power', 0) for record in day_data
                ) * (len(day_data) / 120)  # Approximate kWh (assuming 30s intervals)
                
                daily_consumptions.append({
                    'date': day,
                    'consumption': total_consumption,
                    'weekday': day.weekday()
                })
            
            # Calculate statistics
            consumptions = [d['consumption'] for d in daily_consumptions]
            avg_consumption = statistics.mean(consumptions)
            peak_consumption = max(consumptions)
            min_consumption = min(consumptions)
            
            # Find patterns by weekday
            weekday_patterns = self._analyze_weekday_patterns(daily_consumptions)
            peak_hour = max(weekday_patterns.keys(), key=lambda d: weekday_patterns[d])
            low_hour = min(weekday_patterns.keys(), key=lambda d: weekday_patterns[d])
            
            # Detect trend
            trend = self._detect_daily_trend(daily_consumptions)
            
            # Calculate efficiency score
            efficiency_score = self._calculate_daily_efficiency(daily_data)
            
            # Detect anomalies
            anomalies = self._detect_daily_anomalies(daily_consumptions)
            
            pattern_confidence = self._calculate_daily_pattern_confidence(daily_consumptions)
            
            return ConsumptionPattern(
                period_type='daily',
                timestamp=datetime.now(timezone.utc),
                avg_consumption=avg_consumption,
                peak_consumption=peak_consumption,
                min_consumption=min_consumption,
                peak_hour=peak_hour,
                low_hour=low_hour,
                trend=trend,
                efficiency_score=efficiency_score,
                pattern_confidence=pattern_confidence,
                anomalies=anomalies
            )
            
        except Exception as e:
            logger.error(f"Error in daily consumption analysis: {e}")
            return self._create_empty_pattern('daily')
    
    async def analyze_battery_usage(self) -> BatteryAnalysis:
        """Analyze battery usage patterns and optimization opportunities."""
        try:
            # Get recent battery data
            data = await self.db_manager.get_historical_data(
                'solar_metrics',
                '-24h',
                None
            )
            
            if not data:
                logger.warning("No data available for battery analysis")
                return self._create_empty_battery_analysis()
            
            # Extract battery data
            battery_data = []
            for record in data:
                if all(key in record for key in ['battery_soc', 'battery_power', 'solar_power']):
                    battery_data.append({
                        'timestamp': record['timestamp'],
                        'soc': float(record['battery_soc']),
                        'power': float(record['battery_power']),
                        'solar': float(record['solar_power']),
                        'hour': record['timestamp'].hour
                    })
            
            if len(battery_data) < self.min_data_points:
                return self._create_empty_battery_analysis()
            
            current_soc = battery_data[-1]['soc']
            
            # Calculate charge/discharge rates
            discharge_rates = []
            charge_rates = []
            
            for i in range(1, len(battery_data)):
                soc_change = battery_data[i]['soc'] - battery_data[i-1]['soc']
                time_diff = (battery_data[i]['timestamp'] - battery_data[i-1]['timestamp']).total_seconds() / 3600
                
                if time_diff > 0:
                    rate = soc_change / time_diff  # %/hour
                    if rate < 0:
                        discharge_rates.append(abs(rate))
                    elif rate > 0:
                        charge_rates.append(rate)
            
            avg_discharge_rate = statistics.mean(discharge_rates) if discharge_rates else 0
            avg_charge_rate = statistics.mean(charge_rates) if charge_rates else 0
            
            # Calculate projected runtime
            if avg_discharge_rate > 0:
                usable_soc = current_soc - self.min_soc
                projected_runtime = usable_soc / avg_discharge_rate
            else:
                projected_runtime = float('inf')
            
            # Find optimal charge window
            optimal_window = self._find_optimal_charge_window(battery_data)
            
            # Find geyser opportunities
            geyser_opportunities = self._find_geyser_opportunities(battery_data)
            
            # Calculate efficiency metrics
            efficiency_metrics = self._calculate_battery_efficiency(battery_data)
            
            return BatteryAnalysis(
                timestamp=datetime.now(timezone.utc),
                current_soc=current_soc,
                avg_discharge_rate=avg_discharge_rate,
                avg_charge_rate=avg_charge_rate,
                projected_runtime=projected_runtime,
                optimal_charge_window=optimal_window,
                geyser_opportunities=geyser_opportunities,
                efficiency_metrics=efficiency_metrics
            )
            
        except Exception as e:
            logger.error(f"Error in battery analysis: {e}")
            return self._create_empty_battery_analysis()
    
    async def analyze_energy_flow(self) -> EnergyFlow:
        """Analyze energy flow patterns and optimization opportunities."""
        try:
            # Get recent data
            data = await self.db_manager.get_historical_data(
                'solar_metrics',
                '-24h',
                None
            )
            
            if not data:
                return self._create_empty_energy_flow()
            
            # Calculate energy flow percentages
            total_solar = sum(record.get('solar_power', 0) for record in data)
            total_load = sum(record.get('load_power', 0) for record in data)
            total_grid_import = sum(max(0, record.get('grid_power', 0)) for record in data)
            total_grid_export = sum(abs(min(0, record.get('grid_power', 0))) for record in data)
            total_battery_charge = sum(abs(min(0, record.get('battery_power', 0))) for record in data)
            total_battery_discharge = sum(max(0, record.get('battery_power', 0)) for record in data)
            
            if total_solar == 0:
                return self._create_empty_energy_flow()
            
            # Calculate flow percentages
            solar_to_load_direct = min(100, (total_load / total_solar) * 100) if total_solar > 0 else 0
            solar_to_battery = (total_battery_charge / total_solar) * 100 if total_solar > 0 else 0
            solar_to_grid = (total_grid_export / total_solar) * 100 if total_solar > 0 else 0
            
            grid_to_load = (total_grid_import / total_load) * 100 if total_load > 0 else 0
            battery_to_load = (total_battery_discharge / total_load) * 100 if total_load > 0 else 0
            
            # Self-consumption ratio
            self_consumed = total_solar - total_grid_export
            self_consumption_ratio = (self_consumed / total_solar) * 100 if total_solar > 0 else 0
            
            # Grid independence
            grid_independence = max(0, 100 - grid_to_load)
            
            # Optimization score
            optimization_score = self._calculate_optimization_score(
                self_consumption_ratio, grid_independence, solar_to_grid
            )
            
            return EnergyFlow(
                timestamp=datetime.now(timezone.utc),
                solar_to_load_direct=solar_to_load_direct,
                solar_to_battery=solar_to_battery,
                solar_to_grid=solar_to_grid,
                grid_to_load=grid_to_load,
                battery_to_load=battery_to_load,
                self_consumption_ratio=self_consumption_ratio,
                grid_independence=grid_independence,
                optimization_score=optimization_score
            )
            
        except Exception as e:
            logger.error(f"Error in energy flow analysis: {e}")
            return self._create_empty_energy_flow()
    
    async def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis."""
        try:
            recommendations = []
            
            # Get recent analyses
            battery_analysis = await self.analyze_battery_usage()
            energy_flow = await self.analyze_energy_flow()
            hourly_pattern = await self.analyze_hourly_consumption()
            
            # Battery optimization recommendations
            if battery_analysis.projected_runtime < 4:
                recommendations.append({
                    'type': 'battery_optimization',
                    'priority': 'high',
                    'title': 'Battery Runtime Warning',
                    'description': f'Battery may run out in {battery_analysis.projected_runtime:.1f} hours at current usage',
                    'actions': [
                        'Reduce non-essential loads',
                        'Check for high power consumption devices',
                        'Consider load shedding schedule'
                    ]
                })
            
            # Geyser usage recommendations
            if battery_analysis.geyser_opportunities:
                next_opportunity = battery_analysis.geyser_opportunities[0]
                recommendations.append({
                    'type': 'geyser_optimization',
                    'priority': 'medium',
                    'title': 'Geyser Usage Opportunity',
                    'description': f'Good time to heat geyser: {next_opportunity["available_time"]:.0f} minutes available',
                    'actions': [
                        'Switch on geyser now',
                        f'Available runtime: {next_opportunity["available_time"]:.0f} minutes',
                        'Monitor battery level'
                    ]
                })
            
            # Self-consumption optimization
            if energy_flow.self_consumption_ratio < 70:
                recommendations.append({
                    'type': 'self_consumption',
                    'priority': 'medium',
                    'title': 'Low Self-Consumption',
                    'description': f'Only {energy_flow.self_consumption_ratio:.1f}% of solar power is self-consumed',
                    'actions': [
                        'Shift loads to daytime hours',
                        'Consider battery capacity upgrade',
                        'Use high-power appliances during peak solar hours'
                    ]
                })
            
            # Peak time optimization
            if hourly_pattern.peak_hour >= 17 and hourly_pattern.peak_hour <= 20:
                recommendations.append({
                    'type': 'peak_time_optimization',
                    'priority': 'medium',
                    'title': 'Peak Hour Usage',
                    'description': f'Highest consumption at {hourly_pattern.peak_hour}:00 (peak tariff hours)',
                    'actions': [
                        'Shift non-essential loads to off-peak hours',
                        'Pre-heat water during solar hours',
                        'Use timer switches for appliances'
                    ]
                })
            
            # Grid independence optimization
            if energy_flow.grid_independence < 50:
                recommendations.append({
                    'type': 'grid_independence',
                    'priority': 'low',
                    'title': 'Grid Independence Opportunity',
                    'description': f'Grid independence is {energy_flow.grid_independence:.1f}%',
                    'actions': [
                        'Consider solar capacity expansion',
                        'Evaluate battery capacity increase',
                        'Implement demand management strategies'
                    ]
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def store_analysis_results(self, analysis_type: str, results: Dict[str, Any]) -> bool:
        """Store analysis results in database."""
        try:
            if analysis_type == 'consumption_pattern':
                pattern = results
                consumption_analysis = ConsumptionAnalysis(
                    timestamp=pattern.timestamp,
                    analysis_type=pattern.period_type,
                    avg_consumption=pattern.avg_consumption,
                    peak_consumption=pattern.peak_consumption,
                    min_consumption=pattern.min_consumption,
                    battery_depletion_rate=0.0,  # Would be calculated from battery analysis
                    projected_runtime=0.0,      # Would be calculated from battery analysis
                    geyser_runtime_available=0.0,  # Would be calculated from battery analysis
                    cost_savings=0.0,           # Would be calculated separately
                    grid_import_cost=0.0,       # Would be calculated separately
                    solar_generation_value=0.0  # Would be calculated separately
                )
                
                return await self.db_manager.write_consumption_analysis(consumption_analysis)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing analysis results: {e}")
            return False
    
    def _calculate_hourly_averages(self, consumption_data: List[Dict]) -> Dict[int, float]:
        """Calculate average consumption by hour."""
        hourly_data = {}
        for record in consumption_data:
            hour = record['hour']
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(record['consumption'])
        
        return {hour: statistics.mean(values) for hour, values in hourly_data.items()}
    
    def _detect_trend(self, consumption_data: List[Dict]) -> str:
        """Detect consumption trend over time."""
        if len(consumption_data) < 3:
            return 'stable'
        
        # Simple linear trend detection
        consumptions = [d['consumption'] for d in consumption_data]
        n = len(consumptions)
        
        # Calculate trend using least squares
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(consumptions)
        sum_xy = sum(x[i] * consumptions[i] for i in range(n))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.01:
            return 'increasing'
        elif slope < -0.01:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_efficiency_score(self, consumption_data: List[Dict], solar_data: List[Dict]) -> float:
        """Calculate efficiency score based on consumption patterns."""
        # This is a simplified efficiency calculation
        # In practice, you'd want more sophisticated metrics
        
        if not consumption_data or not solar_data:
            return 0.0
        
        # Base score on load factor (how consistently power is used)
        consumptions = [d['consumption'] for d in consumption_data]
        if not consumptions:
            return 0.0
        
        avg_consumption = statistics.mean(consumptions)
        peak_consumption = max(consumptions)
        
        if peak_consumption == 0:
            return 0.0
        
        load_factor = avg_consumption / peak_consumption
        
        # Convert to 0-100 score (higher load factor is generally better)
        return min(100.0, load_factor * 100)
    
    def _detect_consumption_anomalies(self, consumption_data: List[Dict]) -> List[Dict[str, Any]]:
        """Detect consumption anomalies."""
        if len(consumption_data) < 10:
            return []
        
        consumptions = [d['consumption'] for d in consumption_data]
        mean_consumption = statistics.mean(consumptions)
        std_consumption = statistics.stdev(consumptions)
        
        anomalies = []
        threshold = 2.0  # 2 standard deviations
        
        for record in consumption_data:
            z_score = abs(record['consumption'] - mean_consumption) / std_consumption
            if z_score > threshold:
                anomalies.append({
                    'timestamp': record['timestamp'],
                    'consumption': record['consumption'],
                    'z_score': z_score,
                    'type': 'high' if record['consumption'] > mean_consumption else 'low'
                })
        
        return anomalies
    
    def _calculate_pattern_confidence(self, consumption_data: List[Dict]) -> float:
        """Calculate confidence in the consumption pattern."""
        if len(consumption_data) < 5:
            return 0.0
        
        consumptions = [d['consumption'] for d in consumption_data]
        mean_consumption = statistics.mean(consumptions)
        std_consumption = statistics.stdev(consumptions)
        
        # Higher confidence for more consistent patterns
        if mean_consumption == 0:
            return 0.0
        
        coefficient_of_variation = std_consumption / mean_consumption
        confidence = max(0.0, 1.0 - coefficient_of_variation)
        
        return min(1.0, confidence)
    
    def _group_data_by_day(self, data: List[Dict]) -> Dict[datetime, List[Dict]]:
        """Group data by day."""
        daily_data = {}
        for record in data:
            day = record['timestamp'].replace(hour=0, minute=0, second=0, microsecond=0)
            if day not in daily_data:
                daily_data[day] = []
            daily_data[day].append(record)
        
        return daily_data
    
    def _analyze_weekday_patterns(self, daily_consumptions: List[Dict]) -> Dict[int, float]:
        """Analyze consumption patterns by weekday."""
        weekday_data = {}
        for record in daily_consumptions:
            weekday = record['weekday']
            if weekday not in weekday_data:
                weekday_data[weekday] = []
            weekday_data[weekday].append(record['consumption'])
        
        return {weekday: statistics.mean(values) for weekday, values in weekday_data.items()}
    
    def _detect_daily_trend(self, daily_consumptions: List[Dict]) -> str:
        """Detect daily consumption trend."""
        if len(daily_consumptions) < 3:
            return 'stable'
        
        # Sort by date
        sorted_data = sorted(daily_consumptions, key=lambda x: x['date'])
        consumptions = [d['consumption'] for d in sorted_data]
        
        # Simple trend detection
        first_half = consumptions[:len(consumptions)//2]
        second_half = consumptions[len(consumptions)//2:]
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        change_percent = ((avg_second - avg_first) / avg_first) * 100 if avg_first > 0 else 0
        
        if change_percent > 10:
            return 'increasing'
        elif change_percent < -10:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_daily_efficiency(self, daily_data: Dict[datetime, List[Dict]]) -> float:
        """Calculate daily efficiency score."""
        # Simplified daily efficiency calculation
        total_score = 0
        days_counted = 0
        
        for day, day_records in daily_data.items():
            if len(day_records) < 10:  # Need sufficient data points
                continue
            
            consumptions = [r.get('load_power', 0) for r in day_records]
            solar_powers = [r.get('solar_power', 0) for r in day_records]
            
            if not consumptions or not solar_powers:
                continue
            
            avg_consumption = statistics.mean(consumptions)
            avg_solar = statistics.mean(solar_powers)
            
            # Simple efficiency metric: how well consumption aligns with solar production
            if avg_solar > 0:
                efficiency = min(100, (avg_consumption / avg_solar) * 100)
                total_score += efficiency
                days_counted += 1
        
        return total_score / days_counted if days_counted > 0 else 0.0
    
    def _detect_daily_anomalies(self, daily_consumptions: List[Dict]) -> List[Dict[str, Any]]:
        """Detect daily consumption anomalies."""
        if len(daily_consumptions) < 5:
            return []
        
        consumptions = [d['consumption'] for d in daily_consumptions]
        mean_consumption = statistics.mean(consumptions)
        std_consumption = statistics.stdev(consumptions)
        
        anomalies = []
        threshold = 1.5  # 1.5 standard deviations for daily data
        
        for record in daily_consumptions:
            z_score = abs(record['consumption'] - mean_consumption) / std_consumption
            if z_score > threshold:
                anomalies.append({
                    'date': record['date'],
                    'consumption': record['consumption'],
                    'z_score': z_score,
                    'type': 'high' if record['consumption'] > mean_consumption else 'low'
                })
        
        return anomalies
    
    def _calculate_daily_pattern_confidence(self, daily_consumptions: List[Dict]) -> float:
        """Calculate confidence in daily pattern."""
        if len(daily_consumptions) < 3:
            return 0.0
        
        consumptions = [d['consumption'] for d in daily_consumptions]
        mean_consumption = statistics.mean(consumptions)
        std_consumption = statistics.stdev(consumptions)
        
        if mean_consumption == 0:
            return 0.0
        
        coefficient_of_variation = std_consumption / mean_consumption
        confidence = max(0.0, 1.0 - coefficient_of_variation)
        
        return min(1.0, confidence)
    
    def _find_optimal_charge_window(self, battery_data: List[Dict]) -> Tuple[int, int]:
        """Find optimal battery charging window."""
        # Group by hour and find when solar is highest and battery SOC is lowest
        hourly_solar = {}
        hourly_soc = {}
        
        for record in battery_data:
            hour = record['hour']
            if hour not in hourly_solar:
                hourly_solar[hour] = []
                hourly_soc[hour] = []
            
            hourly_solar[hour].append(record['solar'])
            hourly_soc[hour].append(record['soc'])
        
        # Calculate averages
        avg_solar_by_hour = {h: statistics.mean(vals) for h, vals in hourly_solar.items()}
        avg_soc_by_hour = {h: statistics.mean(vals) for h, vals in hourly_soc.items()}
        
        # Find the 4-hour window with highest solar and reasonable SOC
        best_score = 0
        best_window = (10, 14)  # Default to 10 AM - 2 PM
        
        for start_hour in range(8, 16):  # 8 AM to 4 PM
            end_hour = min(start_hour + 4, 18)
            
            window_solar = sum(avg_solar_by_hour.get(h, 0) for h in range(start_hour, end_hour))
            window_soc = statistics.mean([avg_soc_by_hour.get(h, 50) for h in range(start_hour, end_hour)])
            
            # Score based on solar availability and reasonable SOC
            score = window_solar * (1 - window_soc / 100)  # Higher score for more solar and lower SOC
            
            if score > best_score:
                best_score = score
                best_window = (start_hour, end_hour)
        
        return best_window
    
    def _find_geyser_opportunities(self, battery_data: List[Dict]) -> List[Dict[str, Any]]:
        """Find opportunities for geyser usage."""
        opportunities = []
        current_time = datetime.now(timezone.utc)
        
        for record in battery_data:
            # Check if this is a good time for geyser usage
            soc = record['soc']
            solar = record['solar']
            hour = record['hour']
            
            # Good opportunity: High SOC (>70%), decent solar (>1kW), daytime hours
            if soc > 70 and solar > 1.0 and 10 <= hour <= 16:
                # Calculate available time
                usable_soc = soc - self.min_soc
                usable_energy = (usable_soc / 100) * self.battery_capacity_kwh
                available_time = (usable_energy / self.geyser_power_kw) * 60  # minutes
                
                if available_time > 20:  # At least 20 minutes
                    opportunities.append({
                        'timestamp': record['timestamp'],
                        'soc': soc,
                        'solar_power': solar,
                        'available_time': available_time,
                        'confidence': min(1.0, (soc - 70) / 30)  # Confidence based on SOC above 70%
                    })
        
        # Sort by confidence (best opportunities first)
        return sorted(opportunities, key=lambda x: x['confidence'], reverse=True)[:5]
    
    def _calculate_battery_efficiency(self, battery_data: List[Dict]) -> Dict[str, float]:
        """Calculate battery efficiency metrics."""
        if not battery_data:
            return {}
        
        charge_energy = 0
        discharge_energy = 0
        
        for i in range(1, len(battery_data)):
            prev_record = battery_data[i-1]
            curr_record = battery_data[i]
            
            time_diff = (curr_record['timestamp'] - prev_record['timestamp']).total_seconds() / 3600
            power_avg = (abs(prev_record['power']) + abs(curr_record['power'])) / 2
            energy = power_avg * time_diff
            
            if curr_record['power'] < 0:  # Charging
                charge_energy += energy
            elif curr_record['power'] > 0:  # Discharging
                discharge_energy += energy
        
        # Calculate round-trip efficiency
        round_trip_efficiency = (discharge_energy / charge_energy * 100) if charge_energy > 0 else 0
        
        return {
            'round_trip_efficiency': round_trip_efficiency,
            'total_charge_energy': charge_energy,
            'total_discharge_energy': discharge_energy
        }
    
    def _calculate_optimization_score(
        self, 
        self_consumption: float, 
        grid_independence: float, 
        export_ratio: float
    ) -> float:
        """Calculate overall optimization score."""
        # Weighted scoring system
        weights = {
            'self_consumption': 0.4,
            'grid_independence': 0.3,
            'export_utilization': 0.3
        }
        
        # Normalize export ratio (higher is better for financial return)
        export_score = min(100, export_ratio * 2)  # Assume 50% export is excellent
        
        score = (
            self_consumption * weights['self_consumption'] +
            grid_independence * weights['grid_independence'] +
            export_score * weights['export_utilization']
        )
        
        return min(100, score)
    
    def _create_empty_pattern(self, period_type: str) -> ConsumptionPattern:
        """Create empty consumption pattern."""
        return ConsumptionPattern(
            period_type=period_type,
            timestamp=datetime.now(timezone.utc),
            avg_consumption=0.0,
            peak_consumption=0.0,
            min_consumption=0.0,
            peak_hour=12,
            low_hour=3,
            trend='stable',
            efficiency_score=0.0,
            pattern_confidence=0.0,
            anomalies=[]
        )
    
    def _create_empty_battery_analysis(self) -> BatteryAnalysis:
        """Create empty battery analysis."""
        return BatteryAnalysis(
            timestamp=datetime.now(timezone.utc),
            current_soc=0.0,
            avg_discharge_rate=0.0,
            avg_charge_rate=0.0,
            projected_runtime=0.0,
            optimal_charge_window=(10, 14),
            geyser_opportunities=[],
            efficiency_metrics={}
        )
    
    def _create_empty_energy_flow(self) -> EnergyFlow:
        """Create empty energy flow analysis."""
        return EnergyFlow(
            timestamp=datetime.now(timezone.utc),
            solar_to_load_direct=0.0,
            solar_to_battery=0.0,
            solar_to_grid=0.0,
            grid_to_load=0.0,
            battery_to_load=0.0,
            self_consumption_ratio=0.0,
            grid_independence=0.0,
            optimization_score=0.0
        )


# Async test function
async def test_consumption_analyzer():
    """Test function for consumption analyzer."""
    db_manager = DatabaseManager()
    if not await db_manager.connect():
        print("Could not connect to database")
        return
    
    analyzer = ConsumptionAnalyzer(db_manager)
    
    print("Testing consumption analyzer...")
    
    # Test hourly analysis
    hourly_pattern = await analyzer.analyze_hourly_consumption()
    print(f"Hourly Analysis - Avg: {hourly_pattern.avg_consumption:.2f}kW, "
          f"Peak Hour: {hourly_pattern.peak_hour}, Trend: {hourly_pattern.trend}")
    
    # Test battery analysis
    battery_analysis = await analyzer.analyze_battery_usage()
    print(f"Battery Analysis - SOC: {battery_analysis.current_soc:.1f}%, "
          f"Runtime: {battery_analysis.projected_runtime:.1f}h")
    
    # Test recommendations
    recommendations = await analyzer.generate_optimization_recommendations()
    print(f"Generated {len(recommendations)} recommendations")
    for rec in recommendations:
        print(f"- {rec['title']}: {rec['description']}")
    
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(test_consumption_analyzer())