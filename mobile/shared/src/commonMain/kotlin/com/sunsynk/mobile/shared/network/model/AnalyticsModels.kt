package com.sunsynk.mobile.shared.network.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class WeatherCorrelationResponse(
    @SerialName("correlation_coefficient") val correlationCoefficient: Double,
    @SerialName("prediction_accuracy") val predictionAccuracy: Double,
    @SerialName("analysis_period_days") val analysisPeriodDays: Int,
    val location: String? = null,
    @SerialName("current_weather") val currentWeather: WeatherSnapshot? = null,
    @SerialName("daily_predictions") val dailyPredictions: List<WeatherPrediction> = emptyList(),
    @SerialName("confidence_score") val confidenceScore: Double? = null
)

@Serializable
data class WeatherSnapshot(
    val temperature: Double? = null,
    val humidity: Double? = null,
    @SerialName("cloud_cover") val cloudCover: Double? = null,
    val condition: String? = null
)

@Serializable
data class WeatherPrediction(
    val date: String,
    val weather: String,
    @SerialName("predicted_efficiency") val predictedEfficiency: Double
)

@Serializable
data class ConsumptionPatternResponse(
    @SerialName("analysis_period_days") val analysisPeriodDays: Int,
    val patterns: List<ConsumptionPattern> = emptyList(),
    val anomalies: List<ConsumptionAnomaly> = emptyList(),
    @SerialName("optimization_recommendations") val optimizationRecommendations: List<OptimizationRecommendation> = emptyList(),
    @SerialName("efficiency_score") val efficiencyScore: Double,
    @SerialName("last_updated") val lastUpdated: String? = null
)

@Serializable
data class ConsumptionPattern(
    val type: String,
    @SerialName("peak_hours") val peakHours: List<Int> = emptyList(),
    @SerialName("average_consumption") val averageConsumption: Double,
    @SerialName("peak_consumption") val peakConsumption: Double,
    @SerialName("efficiency_score") val efficiencyScore: Double,
    val confidence: Double? = null
)

@Serializable
data class ConsumptionAnomaly(
    val timestamp: String,
    val expected: Double,
    val actual: Double,
    val deviation: Double,
    val type: String,
    val severity: String
)

@Serializable
data class OptimizationRecommendation(
    val category: String,
    val title: String,
    val description: String,
    @SerialName("potential_savings") val potentialSavings: String,
    val confidence: Double,
    val priority: String
)

@Serializable
data class BatteryOptimizationResponse(
    @SerialName("current_strategy") val currentStrategy: String,
    @SerialName("optimal_soc_range") val optimalSocRange: RangeDto,
    @SerialName("charge_schedule") val chargeSchedule: List<BatteryScheduleEntry> = emptyList(),
    @SerialName("discharge_schedule") val dischargeSchedule: List<BatteryScheduleEntry> = emptyList(),
    @SerialName("efficiency_improvements") val efficiencyImprovements: List<EfficiencyImprovement> = emptyList(),
    @SerialName("cost_savings") val costSavings: CostSavings? = null,
    @SerialName("weather_integration") val weatherIntegration: Map<String, String>? = null,
    @SerialName("confidence_score") val confidenceScore: Double,
    @SerialName("last_updated") val lastUpdated: String? = null
)

@Serializable
data class RangeDto(
    val min: Double,
    val max: Double
)

@Serializable
data class BatteryScheduleEntry(
    val time: String,
    @SerialName("target_soc") val targetSoc: Double,
    val source: String? = null,
    val usage: String? = null,
    val priority: String
)

@Serializable
data class EfficiencyImprovement(
    val metric: String,
    val current: String,
    val optimized: String,
    val improvement: Double
)

@Serializable
data class CostSavings(
    @SerialName("monthly_estimate") val monthlyEstimate: String,
    @SerialName("yearly_estimate") val yearlyEstimate: String,
    @SerialName("load_shedding_protection") val loadSheddingProtection: String,
    @SerialName("peak_demand_reduction") val peakDemandReduction: String
)

@Serializable
data class ForecastingResponse(
    @SerialName("forecast_horizon_hours") val forecastHorizonHours: Int,
    @SerialName("production_forecast") val productionForecast: List<ForecastEntry> = emptyList(),
    val summary: ForecastSummary,
    @SerialName("model_performance") val modelPerformance: ForecastModelPerformance,
    val recommendations: List<String>,
    @SerialName("confidence_score") val confidenceScore: Double,
    @SerialName("last_updated") val lastUpdated: String? = null
)

@Serializable
data class ForecastEntry(
    val timestamp: String,
    @SerialName("predicted_production") val predictedProduction: Double,
    @SerialName("predicted_consumption") val predictedConsumption: Double,
    @SerialName("predicted_grid_usage") val predictedGridUsage: Double
)

@Serializable
data class ForecastSummary(
    @SerialName("total_predicted_production") val totalPredictedProduction: Double,
    @SerialName("total_predicted_consumption") val totalPredictedConsumption: Double,
    @SerialName("net_grid_usage") val netGridUsage: Double,
    @SerialName("self_sufficiency_percentage") val selfSufficiencyPercentage: Double,
    @SerialName("peak_production_hour") val peakProductionHour: Int,
    @SerialName("peak_consumption_hour") val peakConsumptionHour: Int
)

@Serializable
data class ForecastModelPerformance(
    @SerialName("accuracy_last_7_days") val accuracyLast7Days: Double,
    @SerialName("mae_production") val maeProduction: Double,
    @SerialName("mae_consumption") val maeConsumption: Double,
    @SerialName("model_version") val modelVersion: String
)
