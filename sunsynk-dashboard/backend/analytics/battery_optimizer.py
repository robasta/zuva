"""
Battery Optimization Scheduler - Phase 6 Task 070
Machine learning models for battery optimization scheduling
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class BatteryMode(Enum):
    CHARGE = "charge"
    DISCHARGE = "discharge"
    HOLD = "hold"
    AUTO = "auto"

@dataclass
class BatterySchedule:
    """Battery scheduling recommendation"""
    timestamp: datetime
    mode: BatteryMode
    target_soc: float  # Target State of Charge (%)
    priority: str  # 'high', 'medium', 'low'
    reason: str
    expected_savings: float  # kWh
    confidence: float

@dataclass
class BatteryHealthMetrics:
    """Battery health and performance metrics"""
    capacity_retention: float  # %
    cycle_count_estimate: int
    efficiency: float  # %
    temperature_factor: float
    degradation_rate: float  # % per month
    health_score: float  # Overall health 0-1

@dataclass
class EnergyFlowOptimization:
    """Energy flow optimization recommendation"""
    timestamp: datetime
    solar_forecast: float
    consumption_forecast: float
    grid_cost: float
    recommended_battery_action: str
    potential_savings: float
    optimization_strategy: str

class BatteryOptimizer:
    """
    Advanced Battery Optimization System
    Uses ML for intelligent battery scheduling and health monitoring
    """
    
    def __init__(self, battery_capacity: float = 5.0, max_charge_rate: float = 2.5):
        self.battery_capacity = battery_capacity  # kWh
        self.max_charge_rate = max_charge_rate    # kW
        self.depth_of_discharge_limit = 0.2      # Don't discharge below 20%
        self.target_soc_range = (0.3, 0.9)       # Optimal SOC range 30-90%
        
        # Time-of-use electricity rates (simplified)
        self.tou_rates = {
            'peak': {'hours': [17, 18, 19, 20], 'rate': 2.5},      # R2.50/kWh
            'standard': {'hours': [6, 7, 8, 9, 21, 22], 'rate': 1.8}, # R1.80/kWh
            'off_peak': {'hours': [0, 1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15, 16, 23], 'rate': 1.2}  # R1.20/kWh
        }
    
    def analyze_battery_health(self, historical_battery_data: List[Dict]) -> BatteryHealthMetrics:
        """
        Analyze battery health using historical data
        """
        if not historical_battery_data or len(historical_battery_data) < 24:
            return BatteryHealthMetrics(
                capacity_retention=95.0,
                cycle_count_estimate=100,
                efficiency=85.0,
                temperature_factor=1.0,
                degradation_rate=0.1,
                health_score=0.9
            )
        
        try:
            df = pd.DataFrame(historical_battery_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # Calculate battery efficiency
            charge_cycles = self._detect_charge_cycles(df)
            efficiency = self._calculate_round_trip_efficiency(charge_cycles)
            
            # Estimate cycle count (simplified)
            days_of_data = (df.index[-1] - df.index[0]).days or 1
            cycles_per_day = len(charge_cycles) / days_of_data
            estimated_total_cycles = int(cycles_per_day * 365)  # Annualized
            
            # Calculate capacity retention (simplified degradation model)
            # Typical Li-ion loses ~0.1% per cycle + ~0.05% per month calendar aging
            cycle_degradation = estimated_total_cycles * 0.001  # 0.1% per cycle
            calendar_degradation = days_of_data / 30 * 0.0005   # 0.05% per month
            capacity_retention = max(80.0, 100.0 - (cycle_degradation + calendar_degradation) * 100)
            
            # Temperature factor (assumed normal operation)
            temperature_factor = 1.0  # Would need temperature data for accurate calculation
            
            # Calculate overall health score
            efficiency_score = efficiency / 95.0  # Normalize to 95% ideal efficiency
            capacity_score = capacity_retention / 100.0
            cycle_score = max(0, 1 - (estimated_total_cycles / 6000))  # 6000 cycles lifetime
            
            health_score = (efficiency_score + capacity_score + cycle_score) / 3
            health_score = max(0, min(1, health_score))
            
            # Degradation rate (% per month)
            degradation_rate = (100 - capacity_retention) / (days_of_data / 30) if days_of_data > 30 else 0.1
            
            return BatteryHealthMetrics(
                capacity_retention=round(capacity_retention, 1),
                cycle_count_estimate=estimated_total_cycles,
                efficiency=round(efficiency, 1),
                temperature_factor=temperature_factor,
                degradation_rate=round(degradation_rate, 3),
                health_score=round(health_score, 2)
            )
            
        except Exception as e:
            logger.error(f"Battery health analysis error: {e}")
            return BatteryHealthMetrics(
                capacity_retention=90.0,
                cycle_count_estimate=200,
                efficiency=85.0,
                temperature_factor=1.0,
                degradation_rate=0.1,
                health_score=0.85
            )
    
    def _detect_charge_cycles(self, df: pd.DataFrame) -> List[Dict]:
        """Detect battery charge/discharge cycles"""
        cycles = []
        
        if 'battery_level' not in df.columns:
            return cycles
        
        try:
            battery_soc = df['battery_level'].fillna(0)
            
            # Find local minima and maxima
            local_min = []
            local_max = []
            
            for i in range(1, len(battery_soc) - 1):
                if battery_soc.iloc[i] < battery_soc.iloc[i-1] and battery_soc.iloc[i] < battery_soc.iloc[i+1]:
                    local_min.append((battery_soc.index[i], battery_soc.iloc[i]))
                elif battery_soc.iloc[i] > battery_soc.iloc[i-1] and battery_soc.iloc[i] > battery_soc.iloc[i+1]:
                    local_max.append((battery_soc.index[i], battery_soc.iloc[i]))
            
            # Match charge cycles (min to max with sufficient depth)
            for i, (min_time, min_soc) in enumerate(local_min):
                for max_time, max_soc in local_max:
                    if max_time > min_time and (max_soc - min_soc) > 20:  # At least 20% cycle depth
                        cycles.append({
                            'start_time': min_time,
                            'end_time': max_time,
                            'start_soc': min_soc,
                            'end_soc': max_soc,
                            'depth': max_soc - min_soc
                        })
                        break
            
            return cycles
            
        except Exception as e:
            logger.error(f"Charge cycle detection error: {e}")
            return []
    
    def _calculate_round_trip_efficiency(self, cycles: List[Dict]) -> float:
        """Calculate battery round-trip efficiency"""
        if not cycles:
            return 85.0  # Default efficiency
        
        try:
            # Simplified efficiency calculation
            # In reality, would need charge/discharge energy data
            avg_depth = np.mean([cycle['depth'] for cycle in cycles])
            
            # Typical Li-ion efficiency decreases with depth of discharge
            base_efficiency = 90.0
            depth_penalty = (avg_depth / 100) * 5  # 5% penalty for full cycles
            
            efficiency = max(80.0, base_efficiency - depth_penalty)
            return efficiency
            
        except Exception as e:
            logger.error(f"Efficiency calculation error: {e}")
            return 85.0
    
    def optimize_battery_schedule(self, 
                                solar_forecast: List[Dict],
                                consumption_forecast: List[Dict],
                                current_soc: float,
                                hours_ahead: int = 24) -> List[BatterySchedule]:
        """
        Generate optimized battery schedule based on forecasts
        """
        schedules = []
        
        try:
            # Create combined forecast DataFrame
            forecast_data = []
            now = datetime.now()
            
            for i in range(hours_ahead):
                future_time = now + timedelta(hours=i)
                hour = future_time.hour
                
                # Get forecasted values
                solar_kw = 0.0
                consumption_kw = 1.5  # Default
                
                # Find matching forecasts
                for solar in solar_forecast:
                    if abs((pd.to_datetime(solar['timestamp']) - future_time).total_seconds()) < 3600:
                        solar_kw = solar.get('predicted_solar_power', 0)
                        break
                
                for consumption in consumption_forecast:
                    if abs((pd.to_datetime(consumption['timestamp']) - future_time).total_seconds()) < 3600:
                        consumption_kw = consumption.get('predicted_consumption', 1.5)
                        break
                
                # Get electricity rate for this hour
                rate = self._get_electricity_rate(hour)
                
                forecast_data.append({
                    'timestamp': future_time,
                    'hour': hour,
                    'solar_forecast': solar_kw,
                    'consumption_forecast': consumption_kw,
                    'electricity_rate': rate,
                    'net_energy': solar_kw - consumption_kw
                })
            
            df_forecast = pd.DataFrame(forecast_data)
            
            # Optimize battery schedule
            current_battery_soc = current_soc
            
            for idx, row in df_forecast.iterrows():
                optimization = self._optimize_hour(row, current_battery_soc)
                
                # Update SOC for next hour
                if optimization['mode'] == BatteryMode.CHARGE:
                    charge_amount = min(self.max_charge_rate, 
                                      (optimization['target_soc'] - current_battery_soc) / 100 * self.battery_capacity)
                    current_battery_soc = min(90, current_battery_soc + (charge_amount / self.battery_capacity * 100))
                elif optimization['mode'] == BatteryMode.DISCHARGE:
                    discharge_amount = min(self.max_charge_rate,
                                         (current_battery_soc - optimization['target_soc']) / 100 * self.battery_capacity)
                    current_battery_soc = max(20, current_battery_soc - (discharge_amount / self.battery_capacity * 100))
                
                schedule = BatterySchedule(
                    timestamp=row['timestamp'],
                    mode=optimization['mode'],
                    target_soc=optimization['target_soc'],
                    priority=optimization['priority'],
                    reason=optimization['reason'],
                    expected_savings=optimization['savings'],
                    confidence=optimization['confidence']
                )
                schedules.append(schedule)
            
            return schedules
            
        except Exception as e:
            logger.error(f"Battery optimization error: {e}")
            return []
    
    def _get_electricity_rate(self, hour: int) -> float:
        """Get electricity rate for given hour"""
        for rate_type, rate_info in self.tou_rates.items():
            if hour in rate_info['hours']:
                return rate_info['rate']
        return 1.5  # Default rate
    
    def _optimize_hour(self, forecast_row: Dict, current_soc: float) -> Dict:
        """
        Optimize battery action for a single hour
        """
        hour = forecast_row['hour']
        solar = forecast_row['solar_forecast']
        consumption = forecast_row['consumption_forecast']
        rate = forecast_row['electricity_rate']
        net_energy = forecast_row['net_energy']
        
        # Decision logic
        if solar > consumption * 1.2:  # Excess solar
            # Charge battery during excess solar
            target_soc = min(90, current_soc + 20)
            return {
                'mode': BatteryMode.CHARGE,
                'target_soc': target_soc,
                'priority': 'high',
                'reason': f'Excess solar available ({solar:.1f}kW vs {consumption:.1f}kW consumption)',
                'savings': (solar - consumption) * 0.8,  # 80% efficiency
                'confidence': 0.9
            }
        
        elif rate >= 2.0:  # Peak rate period
            if current_soc > 40:
                # Discharge during peak rates
                target_soc = max(30, current_soc - 15)
                return {
                    'mode': BatteryMode.DISCHARGE,
                    'target_soc': target_soc,
                    'priority': 'high',
                    'reason': f'Peak electricity rate (R{rate:.2f}/kWh) - use battery power',
                    'savings': consumption * (rate - 1.2) * 0.85,  # Save vs off-peak rate
                    'confidence': 0.85
                }
        
        elif rate <= 1.3:  # Off-peak rate
            if current_soc < 70 and solar < 1.0:
                # Charge during off-peak if not enough solar expected
                target_soc = min(85, current_soc + 25)
                return {
                    'mode': BatteryMode.CHARGE,
                    'target_soc': target_soc,
                    'priority': 'medium',
                    'reason': f'Off-peak rate (R{rate:.2f}/kWh) - charge for later use',
                    'savings': 2.5 * (2.0 - rate),  # Future peak rate savings
                    'confidence': 0.7
                }
        
        # Default: maintain current SOC
        return {
            'mode': BatteryMode.HOLD,
            'target_soc': current_soc,
            'priority': 'low',
            'reason': 'Maintain current charge level - no optimization opportunity',
            'savings': 0.0,
            'confidence': 0.6
        }
    
    def generate_energy_flow_optimization(self,
                                        solar_forecast: List[Dict],
                                        consumption_forecast: List[Dict],
                                        current_battery_soc: float) -> List[EnergyFlowOptimization]:
        """
        Generate comprehensive energy flow optimization recommendations
        """
        optimizations = []
        
        try:
            for i in range(24):  # 24-hour optimization
                future_time = datetime.now() + timedelta(hours=i)
                
                # Get forecasts for this hour
                solar_kw = 0.0
                consumption_kw = 1.5
                
                for solar in solar_forecast:
                    if abs((pd.to_datetime(solar['timestamp']) - future_time).total_seconds()) < 3600:
                        solar_kw = solar.get('predicted_solar_power', 0)
                        break
                
                for consumption in consumption_forecast:
                    if abs((pd.to_datetime(consumption['timestamp']) - future_time).total_seconds()) < 3600:
                        consumption_kw = consumption.get('predicted_consumption', 1.5)
                        break
                
                # Calculate optimization
                grid_cost = self._get_electricity_rate(future_time.hour)
                energy_balance = solar_kw - consumption_kw
                
                if energy_balance > 1.0:  # Significant excess solar
                    strategy = "solar_first"
                    action = f"Use {solar_kw:.1f}kW solar, store {energy_balance:.1f}kW excess in battery"
                    savings = energy_balance * grid_cost * 0.8
                    
                elif energy_balance < -1.0 and current_battery_soc > 40:  # High consumption, battery available
                    strategy = "battery_first"
                    action = f"Use battery power to meet {abs(energy_balance):.1f}kW deficit, avoid grid import"
                    savings = abs(energy_balance) * grid_cost * 0.9
                    
                elif grid_cost >= 2.0:  # Peak rate period
                    strategy = "peak_avoidance"
                    action = f"Peak rate period - maximize battery usage, minimize grid import"
                    savings = consumption_kw * (grid_cost - 1.2) * 0.7
                    
                else:  # Normal operation
                    strategy = "balanced"
                    action = f"Standard operation - solar+grid as needed"
                    savings = 0.0
                
                optimization = EnergyFlowOptimization(
                    timestamp=future_time,
                    solar_forecast=solar_kw,
                    consumption_forecast=consumption_kw,
                    grid_cost=grid_cost,
                    recommended_battery_action=action,
                    potential_savings=round(savings, 2),
                    optimization_strategy=strategy
                )
                optimizations.append(optimization)
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Energy flow optimization error: {e}")
            return []

# Global instance
battery_optimizer = BatteryOptimizer(battery_capacity=5.0, max_charge_rate=2.5)
