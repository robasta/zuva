package com.sunsynk.mobile.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryEntry
import com.sunsynk.mobile.shared.network.model.TimeseriesPoint
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class DashboardViewModel(private val repository: SunsynkRepository) : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh(hours: Int = 24, timeRange: String = "-24h", resolution: String = "15m") {
        viewModelScope.launch {
            val currentState = _state.value
            val shouldShowSpinner = currentState.current == null && currentState.history.isEmpty() && currentState.timeseries.isEmpty()
            _state.value = currentState.copy(
                isLoading = shouldShowSpinner,
                isRefreshing = true,
                error = null
            )

            val (currentResult, historyResult, timeseriesResult) = withContext(Dispatchers.IO) {
                coroutineScope {
                    val currentDeferred = async { repository.fetchCurrentDashboard(forceRefresh = false) }
                    val historyDeferred = async { repository.fetchHistory(hours = hours, forceRefresh = false) }
                    val timeseriesDeferred = async {
                        repository.fetchTimeseries(start = timeRange, resolution = resolution, forceRefresh = false)
                    }
                    Triple(currentDeferred.await(), historyDeferred.await(), timeseriesDeferred.await())
                }
            }

            val error = listOf(currentResult, historyResult, timeseriesResult)
                .filterIsInstance<ApiResult.Error>()
                .firstOrNull()?.message

            val servedFromCache = listOf(currentResult, historyResult, timeseriesResult)
                .filterIsInstance<ApiResult.Success<*>>()
                .any { it.fromCache }

            _state.value = _state.value.copy(
                isLoading = false,
                isRefreshing = false,
                current = (currentResult as? ApiResult.Success)?.data,
                history = (historyResult as? ApiResult.Success)?.data?.history ?: emptyList(),
                timeseries = (timeseriesResult as? ApiResult.Success)?.data?.data ?: emptyList(),
                error = error,
                isOffline = servedFromCache
            )
        }
    }
}

data class DashboardUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val current: DashboardCurrentResponse? = null,
    val history: List<DashboardHistoryEntry> = emptyList(),
    val timeseries: List<TimeseriesPoint> = emptyList(),
    val error: String? = null,
    val isOffline: Boolean = false
)
