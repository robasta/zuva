package com.sunsynk.mobile.shared.network.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class NotificationPreferencesDto(
    @SerialName("enabled_channels") val enabledChannels: List<String>,
    @SerialName("quiet_hours_start") val quietHoursStart: String,
    @SerialName("quiet_hours_end") val quietHoursEnd: String,
    @SerialName("severity_thresholds") val severityThresholds: Map<String, String>,
    @SerialName("emergency_voice_calls") val emergencyVoiceCalls: Boolean,
    @SerialName("max_notifications_per_hour") val maxNotificationsPerHour: Int
)

@Serializable
data class SettingsResponse(
    val category: String? = null,
    val settings: Map<String, String?> = emptyMap(),
    @SerialName("user_id") val userId: String? = null
)

@Serializable
data class WeatherLocationConfig(
    @SerialName("location_type") val locationType: String,
    val city: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null
)

@Serializable
data class WeatherLocationResponse(
    @SerialName("weather_location") val weatherLocation: WeatherLocationConfig
)
