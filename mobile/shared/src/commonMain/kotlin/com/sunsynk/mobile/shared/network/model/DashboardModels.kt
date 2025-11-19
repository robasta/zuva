package com.sunsynk.mobile.shared.network.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.Transient

@Serializable
data class DashboardMetrics(
    val timestamp: String,
    @SerialName("solar_power") val solarPower: Double,
    @SerialName("battery_level") val batteryLevel: Double,
    @SerialName("grid_power") val gridPower: Double,
    val consumption: Double,
    @SerialName("weather_condition") val weatherCondition: String? = null,
    val temperature: Double? = null
)

@Serializable
data class DashboardStatus(
    val online: Boolean,
    @SerialName("last_update") val lastUpdate: String,
    @SerialName("inverter_status") val inverterStatus: String,
    @SerialName("battery_status") val batteryStatus: String,
    @SerialName("grid_status") val gridStatus: String
)

@Serializable
data class WeatherForecastEntry(
    @SerialName("timestamp") val timestamp: String? = null,
    @SerialName("time") val time: String? = null,
    val condition: String? = null,
    val temperature: Double? = null
) {
    @Transient
    val resolvedTimestamp: String? = timestamp ?: time
}

@Serializable
data class DashboardCurrentResponse(
    val metrics: DashboardMetrics,
    val status: DashboardStatus,
    @SerialName("weather_forecast") val weatherForecast: List<WeatherForecastEntry> = emptyList()
)

@Serializable
data class DashboardHistoryEntry(
    val timestamp: String,
    @SerialName("solar_power") val solarPower: Double,
    @SerialName("battery_level") val batteryLevel: Double,
    @SerialName("grid_power") val gridPower: Double,
    val consumption: Double,
    @SerialName("battery_power") val batteryPower: Double? = null
)

@Serializable
data class DashboardHistoryResponse(
    val history: List<DashboardHistoryEntry>,
    val source: String? = null,
    val count: Int? = null
)

@Serializable
data class TimeseriesPoint(
    val timestamp: String,
    val generation: Double,
    val consumption: Double,
    @SerialName("battery_soc") val batterySoc: Double,
    @SerialName("battery_level") val batteryLevel: Double
)

@Serializable
data class TimeseriesResponse(
    val success: Boolean,
    val data: List<TimeseriesPoint> = emptyList(),
    val source: String? = null,
    val count: Int? = null,
    val resolution: String? = null,
    @SerialName("time_span") val timeSpan: String? = null
)
