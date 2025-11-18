package com.sunsynk.mobile.shared.repository

import com.sunsynk.mobile.shared.network.SunsynkApiClient
import com.sunsynk.mobile.shared.network.model.AlertNotification
import com.sunsynk.mobile.shared.network.model.AlertSeverity
import com.sunsynk.mobile.shared.network.model.AlertStatus
import com.sunsynk.mobile.shared.network.model.LoginResponse
import com.sunsynk.mobile.shared.network.model.NotificationPreferencesDto
import com.sunsynk.mobile.shared.network.model.WeatherLocationConfig
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.flow.Flow

class SunsynkRepository(private val apiClient: SunsynkApiClient) {

    suspend fun login(username: String, password: String): ApiResult<LoginResponse> =
        apiClient.login(username, password)

    suspend fun fetchCurrentDashboard() = apiClient.getDashboardCurrent()

    suspend fun fetchHistory(hours: Int) = apiClient.getDashboardHistory(hours)

    suspend fun fetchTimeseries(start: String, resolution: String) =
        apiClient.getTimeseries(start, resolution)

    suspend fun fetchAlerts(
        status: AlertStatus? = null,
        severity: AlertSeverity? = null,
        hours: Int = 24
    ) = apiClient.getAlerts(status, severity, hours)

    suspend fun acknowledgeAlert(id: String) = apiClient.acknowledgeAlert(id)

    suspend fun resolveAlert(id: String) = apiClient.resolveAlert(id)

    suspend fun fetchNotificationPreferences(): ApiResult<NotificationPreferencesDto> =
        apiClient.getNotificationPreferences()

    suspend fun updateNotificationPreferences(preferences: NotificationPreferencesDto) =
        apiClient.updateNotificationPreferences(preferences)

    suspend fun fetchWeatherLocation() = apiClient.getWeatherLocation()

    suspend fun updateWeatherLocation(config: WeatherLocationConfig) =
        apiClient.updateWeatherLocation(config)

    suspend fun fetchWeatherCorrelation(days: Int) = apiClient.getWeatherCorrelation(days)

    suspend fun fetchConsumptionPatterns(days: Int) = apiClient.getConsumptionPatterns(days)

    suspend fun fetchBatteryOptimization() = apiClient.getBatteryOptimization()

    suspend fun fetchForecast(hours: Int) = apiClient.getForecast(hours)

    fun observeAlertNotifications(): Flow<ApiResult<AlertNotification>> = apiClient.observeAlerts()
}
