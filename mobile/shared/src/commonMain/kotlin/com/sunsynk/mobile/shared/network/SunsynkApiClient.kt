package com.sunsynk.mobile.shared.network

import com.sunsynk.mobile.shared.network.model.AlertNotification
import com.sunsynk.mobile.shared.network.model.AlertSeverity
import com.sunsynk.mobile.shared.network.model.AlertStatus
import com.sunsynk.mobile.shared.network.model.AlertsResponse
import com.sunsynk.mobile.shared.network.model.BatteryOptimizationResponse
import com.sunsynk.mobile.shared.network.model.ConsumptionPatternResponse
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryResponse
import com.sunsynk.mobile.shared.network.model.ForecastingResponse
import com.sunsynk.mobile.shared.network.model.LoginRequest
import com.sunsynk.mobile.shared.network.model.LoginResponse
import com.sunsynk.mobile.shared.network.model.NotificationPreferencesDto
import com.sunsynk.mobile.shared.network.model.SettingsResponse
import com.sunsynk.mobile.shared.network.model.TimeseriesResponse
import com.sunsynk.mobile.shared.network.model.WeatherCorrelationResponse
import com.sunsynk.mobile.shared.network.model.WeatherLocationConfig
import com.sunsynk.mobile.shared.network.model.WeatherLocationResponse
import com.sunsynk.mobile.shared.util.ApiResult
import com.sunsynk.mobile.shared.util.ApiResult.Error
import com.sunsynk.mobile.shared.util.ApiResult.Success
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.websocket.Frame
import io.ktor.websocket.WebSocketSession
import io.ktor.websocket.close
import io.ktor.websocket.readText
import io.ktor.websocket.webSocket
import kotlinx.coroutines.channels.receive
import kotlinx.coroutines.channels.send
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.isActive
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.parseToJsonElement
import kotlinx.serialization.json.jsonObject

class SunsynkApiClient(
    private val httpClient: HttpClient,
    private val config: SunsynkApiConfig,
    private val tokenProvider: suspend () -> String?
) {

    suspend fun login(username: String, password: String): ApiResult<LoginResponse> = safeRequest {
        httpClient.post("${config.baseUrl}/auth/login") {
            contentType(ContentType.Application.Json)
            setBody(LoginRequest(username = username, password = password))
        }
    }

    suspend fun getDashboardCurrent(): ApiResult<DashboardCurrentResponse> = authorizedGet("/dashboard/current")

    suspend fun getDashboardHistory(hours: Int = 24): ApiResult<DashboardHistoryResponse> = authorizedGet("/dashboard/history") {
        parameter("hours", hours)
    }

    suspend fun getTimeseries(start: String = "-24h", resolution: String = "15m"): ApiResult<TimeseriesResponse> = authorizedGet("/dashboard/timeseries") {
        parameter("start_time", start)
        parameter("resolution", resolution)
    }

    suspend fun getAlerts(status: AlertStatus? = null, severity: AlertSeverity? = null, hours: Int = 24): ApiResult<AlertsResponse> = authorizedGet("/alerts") {
        status?.let { parameter("status", it.name.lowercase()) }
        severity?.let { parameter("severity", it.name.lowercase()) }
        parameter("hours", hours)
    }

    suspend fun acknowledgeAlert(alertId: String): ApiResult<Unit> = authorizedPost("/alerts/$alertId/acknowledge")

    suspend fun resolveAlert(alertId: String): ApiResult<Unit> = authorizedPost("/alerts/$alertId/resolve")

    suspend fun getNotificationPreferences(): ApiResult<NotificationPreferencesDto> = authorizedGet("/notifications/preferences")

    suspend fun updateNotificationPreferences(preferences: NotificationPreferencesDto): ApiResult<Unit> = authorizedPost(
        endpoint = "/notifications/preferences",
        payload = preferences
    )

    suspend fun getWeatherLocation(): ApiResult<WeatherLocationResponse> = authorizedGet("/settings/weather/location")

    suspend fun updateWeatherLocation(configPayload: WeatherLocationConfig): ApiResult<Unit> = authorizedPost(
        endpoint = "/settings/weather/location",
        payload = configPayload
    )

    suspend fun getSettings(category: String? = null): ApiResult<SettingsResponse> = when {
        category == null -> authorizedGet("/settings")
        else -> authorizedGet("/settings/$category")
    }

    suspend fun getWeatherCorrelation(days: Int = 7): ApiResult<WeatherCorrelationResponse> = authorizedGet("/v6/weather/correlation") {
        parameter("days", days)
    }

    suspend fun getConsumptionPatterns(days: Int = 30): ApiResult<ConsumptionPatternResponse> = authorizedGet("/v6/consumption/patterns") {
        parameter("days", days)
    }

    suspend fun getBatteryOptimization(): ApiResult<BatteryOptimizationResponse> = authorizedGet("/v6/battery/optimization")

    suspend fun getForecast(hours: Int = 48): ApiResult<ForecastingResponse> = authorizedGet("/v6/analytics/forecasting") {
        parameter("hours", hours)
    }

    fun observeAlerts(): Flow<ApiResult<AlertNotification>> = channelFlow {
        val token = tokenProvider()
        if (token == null) {
            trySend(Error("Missing auth token for WebSocket connection"))
            close()
            return@channelFlow
        }

        val json = Json { ignoreUnknownKeys = true }

        try {
            httpClient.webSocket(urlString = config.websocketUrl, request = {
                header(HttpHeaders.Authorization, "Bearer $token")
            }) {
                try {
                    while (isActive) {
                        when (val frame = incoming.receive()) {
                            is Frame.Text -> {
                                val payload = json.parseToJsonElement(frame.readText())
                                val data = json.decodeFromJsonElement<AlertNotification>(payload)
                                this@channelFlow.send(Success(data))
                            }
                            is Frame.Close -> return@webSocket
                            else -> Unit
                        }
                    }
                } finally {
                    close()
                }
            }
        } catch (e: Exception) {
            trySend(Error("WebSocket connection failed", e))
        }
    }

    private suspend inline fun <reified T> authorizedGet(
        endpoint: String,
        crossinline configBlock: io.ktor.client.request.HttpRequestBuilder.() -> Unit = {}
    ): ApiResult<T> = safeRequest {
        httpClient.get("${config.baseUrl}$endpoint") {
            applyAuthorization()
            configBlock()
        }
    }

    private suspend inline fun <reified T, reified P : Any> authorizedPost(
        endpoint: String,
        payload: P? = null,
        crossinline configBlock: io.ktor.client.request.HttpRequestBuilder.() -> Unit = {}
    ): ApiResult<T> = safeRequest {
        httpClient.post("${config.baseUrl}$endpoint") {
            applyAuthorization()
            contentType(ContentType.Application.Json)
            payload?.let { setBody(it) }
            configBlock()
        }
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.applyAuthorization() {
        tokenProvider()?.let { header(HttpHeaders.Authorization, "Bearer $it") }
    }

    private suspend inline fun <reified T> safeRequest(
        crossinline block: suspend () -> HttpResponse
    ): ApiResult<T> = try {
        val response = block()
        when (response.status) {
            HttpStatusCode.OK, HttpStatusCode.Created, HttpStatusCode.Accepted, HttpStatusCode.NoContent -> {
                if (response.status == HttpStatusCode.NoContent) {
                    @Suppress("UNCHECKED_CAST")
                    Success(Unit as T)
                } else {
                    Success(response.body())
                }
            }
            HttpStatusCode.Unauthorized -> Error("Unauthorized")
            else -> Error("Request failed with status ${response.status.value}")
        }
    } catch (timeout: HttpRequestTimeoutException) {
        Error("Request timed out", timeout)
    } catch (ex: Exception) {
        Error(ex.message ?: "Unknown error", ex)
    }

}
