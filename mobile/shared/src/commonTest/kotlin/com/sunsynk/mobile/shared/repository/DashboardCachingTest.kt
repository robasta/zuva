package com.sunsynk.mobile.shared.repository

import com.sunsynk.mobile.shared.cache.CachedValue
import com.sunsynk.mobile.shared.cache.CachePolicy
import com.sunsynk.mobile.shared.cache.DashboardCache
import com.sunsynk.mobile.shared.network.SunsynkApiClient
import com.sunsynk.mobile.shared.network.SunsynkApiConfig
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryResponse
import com.sunsynk.mobile.shared.network.model.DashboardMetrics
import com.sunsynk.mobile.shared.network.model.DashboardStatus
import com.sunsynk.mobile.shared.network.model.TimeseriesResponse
import com.sunsynk.mobile.shared.util.ApiResult
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.test.runTest
import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlinx.datetime.minus
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class DashboardCachingTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `fetchCurrentDashboard caches successful responses`() = runTest {
        val response = sampleCurrent()
        val engine = MockEngine { _ ->
            respondJson(json.encodeToString(DashboardCurrentResponse.serializer(), response))
        }
        val cache = FakeDashboardCache()
        val repository = createRepository(engine, cache)

        val result = repository.fetchCurrentDashboard()

        val success = assertIs<ApiResult.Success<DashboardCurrentResponse>>(result)
        assertEquals(false, success.fromCache)
        assertEquals(response, cache.current?.data)
    }

    @Test
    fun `fetchCurrentDashboard falls back to cache when network fails`() = runTest {
        val response = sampleCurrent()
        val cache = FakeDashboardCache().apply {
            seedCurrent(response, Clock.System.now())
        }
        val engine = MockEngine { _ ->
            respond(
                content = "",
                status = HttpStatusCode.InternalServerError,
                headers = headersOf(HttpHeaders.ContentType, ContentType.Application.Json.toString())
            )
        }
        val repository = createRepository(engine, cache)

        val result = repository.fetchCurrentDashboard()

        val success = assertIs<ApiResult.Success<DashboardCurrentResponse>>(result)
        assertTrue(success.fromCache)
        assertEquals(response, success.data)
    }

    @Test
    fun `fetchCurrentDashboard returns error when cache is stale`() = runTest {
        val cache = FakeDashboardCache().apply {
            seedCurrent(sampleCurrent(), Clock.System.now().minus(CachePolicy.DEFAULT_TTL * 2))
        }
        val engine = MockEngine { _ ->
            respond(
                content = "",
                status = HttpStatusCode.InternalServerError,
                headers = headersOf(HttpHeaders.ContentType, ContentType.Application.Json.toString())
            )
        }
        val repository = createRepository(engine, cache)

        val result = repository.fetchCurrentDashboard()

        assertIs<ApiResult.Error>(result)
    }

    @Test
    fun `force refresh bypasses cache fallback`() = runTest {
        val cache = FakeDashboardCache().apply {
            seedCurrent(sampleCurrent(), Clock.System.now())
        }
        val engine = MockEngine { _ ->
            respond(
                content = "",
                status = HttpStatusCode.InternalServerError,
                headers = headersOf(HttpHeaders.ContentType, ContentType.Application.Json.toString())
            )
        }
        val repository = createRepository(engine, cache)

        val result = repository.fetchCurrentDashboard(forceRefresh = true)

        assertIs<ApiResult.Error>(result)
    }

    private fun createRepository(engine: MockEngine, cache: DashboardCache): SunsynkRepository {
        val httpClient = HttpClient(engine) {
            install(ContentNegotiation) { json(json) }
        }
        val apiClient = SunsynkApiClient(
            httpClient = httpClient,
            config = SunsynkApiConfig(baseUrl = "http://test"),
            tokenProvider = { "token" }
        )
        return SunsynkRepository(apiClient = apiClient, dashboardCache = cache)
    }

    private fun sampleCurrent(): DashboardCurrentResponse = DashboardCurrentResponse(
        metrics = DashboardMetrics(
            timestamp = "2025-11-18T10:00:00Z",
            solarPower = 4.2,
            batteryLevel = 73.0,
            gridPower = -1.2,
            consumption = 3.8,
            weatherCondition = "sunny",
            temperature = 24.0
        ),
        status = DashboardStatus(
            online = true,
            lastUpdate = "2025-11-18T10:00:00Z",
            inverterStatus = "active",
            batteryStatus = "charging",
            gridStatus = "exporting"
        ),
        weatherForecast = emptyList()
    )

    private class FakeDashboardCache : DashboardCache {
        var current: CachedValue<DashboardCurrentResponse>? = null
        private val history: MutableMap<Int, CachedValue<DashboardHistoryResponse>> = mutableMapOf()
        private val timeseries: MutableMap<String, CachedValue<TimeseriesResponse>> = mutableMapOf()

        override suspend fun saveCurrent(response: DashboardCurrentResponse) {
            current = CachedValue(response, Clock.System.now())
        }

        override suspend fun saveHistory(hours: Int, response: DashboardHistoryResponse) {
            history[hours] = CachedValue(response, Clock.System.now())
        }

        override suspend fun saveTimeseries(start: String, resolution: String, response: TimeseriesResponse) {
            timeseries[timeseriesKey(start, resolution)] = CachedValue(response, Clock.System.now())
        }

        override suspend fun getCurrent(): CachedValue<DashboardCurrentResponse>? = current

        override suspend fun getHistory(hours: Int): CachedValue<DashboardHistoryResponse>? = history[hours]

        override suspend fun getTimeseries(start: String, resolution: String): CachedValue<TimeseriesResponse>? =
            timeseries[timeseriesKey(start, resolution)]

        override suspend fun prune(olderThan: Instant) {
            if (current?.timestamp?.let { it < olderThan } == true) {
                current = null
            }
            history.entries.removeIf { it.value.timestamp < olderThan }
            timeseries.entries.removeIf { it.value.timestamp < olderThan }
        }

        fun seedCurrent(response: DashboardCurrentResponse, timestamp: Instant) {
            current = CachedValue(response, timestamp)
        }

        private fun timeseriesKey(start: String, resolution: String): String = "$start|$resolution"
    }

    private fun MockEngine.respondJson(body: String) = respond(
        content = body,
        status = HttpStatusCode.OK,
        headers = headersOf(HttpHeaders.ContentType, ContentType.Application.Json.toString())
    )
}
