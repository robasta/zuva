package com.sunsynk.mobile.shared.network.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class AlertSeverity {
    @SerialName("low") LOW,
    @SerialName("medium") MEDIUM,
    @SerialName("high") HIGH,
    @SerialName("critical") CRITICAL
}

@Serializable
enum class AlertStatus {
    @SerialName("active") ACTIVE,
    @SerialName("acknowledged") ACKNOWLEDGED,
    @SerialName("resolved") RESOLVED
}

@Serializable
data class AlertDto(
    val id: String,
    val title: String,
    val message: String,
    val severity: AlertSeverity,
    val status: AlertStatus,
    val category: String,
    val timestamp: String,
    @SerialName("acknowledged_at") val acknowledgedAt: String? = null,
    @SerialName("resolved_at") val resolvedAt: String? = null,
    val metadata: Map<String, String?> = emptyMap()
)

@Serializable
data class AlertsResponse(
    val alerts: List<AlertDto>? = null,
    val success: Boolean? = null,
    val count: Int? = null
)

@Serializable
data class AlertNotification(
    val type: String,
    val data: AlertNotificationPayload
)

@Serializable
data class AlertNotificationPayload(
    val id: String,
    val title: String,
    val message: String,
    val severity: AlertSeverity,
    val category: String,
    val timestamp: String
)
