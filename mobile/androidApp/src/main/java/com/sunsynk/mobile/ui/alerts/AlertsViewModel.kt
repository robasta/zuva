package com.sunsynk.mobile.ui.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sunsynk.mobile.data.local.AlertEntity
import com.sunsynk.mobile.data.local.AlertLocalDataSource
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AlertsViewModel(
    private val repository: SunsynkRepository,
    private val localDataSource: AlertLocalDataSource
) : ViewModel() {

    private val _uiState = MutableStateFlow(AlertsUiState())
    val uiState: StateFlow<AlertsUiState> = _uiState.asStateFlow()

    val alerts: StateFlow<List<AlertEntity>> = localDataSource.observeAlerts()
        .map { it.sortedByDescending(AlertEntity::timestamp) }
        .stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

    init {
        refresh()
    }

    fun refresh(hours: Int = 24) {
        viewModelScope.launch {
            val current = _uiState.value
            val shouldShowSpinner = alerts.value.isEmpty()
            _uiState.value = current.copy(
                isLoading = shouldShowSpinner,
                isRefreshing = true,
                error = null
            )
            when (val result = withContext(Dispatchers.IO) { repository.fetchAlerts(hours = hours) }) {
                is ApiResult.Success -> {
                    withContext(Dispatchers.IO) {
                        localDataSource.sync(result.data.alerts.orEmpty())
                    }
                    _uiState.value = AlertsUiState(isLoading = false, isRefreshing = false)
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = result.message
                    )
                }
            }
        }
    }

    fun acknowledge(alert: AlertEntity) {
        viewModelScope.launch {
            when (withContext(Dispatchers.IO) { repository.acknowledgeAlert(alert.id) }) {
                is ApiResult.Success -> refresh()
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = "Unable to acknowledge alert")
            }
        }
    }

    fun resolve(alert: AlertEntity) {
        viewModelScope.launch {
            when (withContext(Dispatchers.IO) { repository.resolveAlert(alert.id) }) {
                is ApiResult.Success -> refresh()
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = "Unable to resolve alert")
            }
        }
    }

}

data class AlertsUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null
)
