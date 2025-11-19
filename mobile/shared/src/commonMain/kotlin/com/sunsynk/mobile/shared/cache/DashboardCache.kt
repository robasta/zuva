package com.sunsynk.mobile.shared.cache

import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryResponse
import com.sunsynk.mobile.shared.network.model.TimeseriesResponse
import kotlinx.datetime.Instant

interface DashboardCache {
    suspend fun saveCurrent(response: DashboardCurrentResponse)
    suspend fun saveHistory(hours: Int, response: DashboardHistoryResponse)
    suspend fun saveTimeseries(start: String, resolution: String, response: TimeseriesResponse)

    suspend fun getCurrent(): CachedValue<DashboardCurrentResponse>?
    suspend fun getHistory(hours: Int): CachedValue<DashboardHistoryResponse>?
    suspend fun getTimeseries(start: String, resolution: String): CachedValue<TimeseriesResponse>?

    suspend fun prune(olderThan: Instant)
}
