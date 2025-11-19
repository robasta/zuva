package com.sunsynk.mobile.shared.repository

import com.sunsynk.mobile.shared.cache.CachePolicy
import com.sunsynk.mobile.shared.cache.CachedValue
import com.sunsynk.mobile.shared.cache.DashboardCache
import com.sunsynk.mobile.shared.cache.expirationThreshold
import com.sunsynk.mobile.shared.cache.isFresh
import com.sunsynk.mobile.shared.network.SunsynkApiClient
import com.sunsynk.mobile.shared.network.model.AlertNotification
import com.sunsynk.mobile.shared.network.model.AlertSeverity
import com.sunsynk.mobile.shared.network.model.AlertStatus
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryResponse
import com.sunsynk.mobile.shared.network.model.LoginResponse
import com.sunsynk.mobile.shared.network.model.NotificationPreferencesDto
import com.sunsynk.mobile.shared.network.model.TimeseriesResponse
import com.sunsynk.mobile.shared.network.model.WeatherLocationConfig
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.flow.Flow

class SunsynkRepository(
    private val apiClient: SunsynkApiClient,
    private val dashboardCache: DashboardCache? = null
) {

    suspend fun login(username: String, password: String): ApiResult<LoginResponse> =
        apiClient.login(username, password)

    suspend fun fetchCurrentDashboard(forceRefresh: Boolean = false): ApiResult<DashboardCurrentResponse> =
        fetchWithCache(
            forceRefresh = forceRefresh,
            fetchRemote = { apiClient.getDashboardCurrent() },
            getCached = { dashboardCache?.getCurrent() },
            saveRemote = { value ->
                dashboardCache?.let { cache ->
                    cache.prune(expirationThreshold(CachePolicy.DEFAULT_TTL))
                    cache.saveCurrent(value)
                }
            }
        )

    suspend fun fetchHistory(hours: Int, forceRefresh: Boolean = false): ApiResult<DashboardHistoryResponse> =
        fetchWithCache(
            forceRefresh = forceRefresh,
            fetchRemote = { apiClient.getDashboardHistory(hours) },
            getCached = { dashboardCache?.getHistory(hours) },
            saveRemote = { value ->
                dashboardCache?.let { cache ->
                    cache.prune(expirationThreshold(CachePolicy.DEFAULT_TTL))
                    cache.saveHistory(hours, value)
                }
            }
        )

    suspend fun fetchTimeseries(
        start: String,
        resolution: String,
        forceRefresh: Boolean = false
    ): ApiResult<TimeseriesResponse> =
        fetchWithCache(
            forceRefresh = forceRefresh,
            fetchRemote = { apiClient.getTimeseries(start, resolution) },
            getCached = { dashboardCache?.getTimeseries(start, resolution) },
            saveRemote = { value ->
                dashboardCache?.let { cache ->
                    cache.prune(expirationThreshold(CachePolicy.DEFAULT_TTL))
                    cache.saveTimeseries(start, resolution, value)
                }
            }
        )

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

private suspend fun <T> fetchWithCache(
    forceRefresh: Boolean,
    fetchRemote: suspend () -> ApiResult<T>,
    getCached: suspend () -> CachedValue<T>?,
    saveRemote: suspend (T) -> Unit
): ApiResult<T> {
    return when (val result = fetchRemote()) {
        is ApiResult.Success -> {
            saveRemote(result.data)
            result
        }
        is ApiResult.Error -> {
            val fallback = if (!forceRefresh) getCached()?.takeIf { it.isFresh() } else null
            fallback?.let { ApiResult.Success(it.data, fromCache = true) } ?: result
        }
    }
}
