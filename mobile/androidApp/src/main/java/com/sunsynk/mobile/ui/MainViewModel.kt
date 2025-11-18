package com.sunsynk.mobile.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sunsynk.mobile.shared.auth.AuthRepository
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainViewModel(
    private val authRepository: AuthRepository,
    private val repository: SunsynkRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<MainUiState>(MainUiState.LoggedOut)
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()

    fun login(username: String, password: String) {
        viewModelScope.launch {
            _uiState.value = MainUiState.Loading
            when (val result = authRepository.login(username, password)) {
                is ApiResult.Success -> _uiState.value = MainUiState.LoggedIn
                is ApiResult.Error -> _uiState.value = MainUiState.Error(result.message)
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _uiState.value = MainUiState.LoggedOut
        }
    }
}

sealed interface MainUiState {
    data object LoggedOut : MainUiState
    data object Loading : MainUiState
    data object LoggedIn : MainUiState
    data class Error(val message: String) : MainUiState
}package com.sunsynk.mobile.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sunsynk.mobile.shared.auth.AuthRepository
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class MainUiState {
    object Loading : MainUiState()
    data class Unauthenticated(val message: String? = null) : MainUiState()
    data class Dashboard(val data: DashboardCurrentResponse) : MainUiState()
    data class Error(val message: String) : MainUiState()
}

class MainViewModel(
    private val authRepository: AuthRepository,
    private val repository: SunsynkRepository
) : ViewModel() {

    private val _uiState: MutableStateFlow<MainUiState> = MutableStateFlow(MainUiState.Loading)
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()

    fun bootstrap() {
        viewModelScope.launch {
            val token = authRepository.currentToken()
            if (token == null) {
                _uiState.value = MainUiState.Unauthenticated()
                return@launch
            }
            fetchDashboard()
        }
    }

    fun login(username: String, password: String) {
        _uiState.value = MainUiState.Loading
        viewModelScope.launch {
            when (authRepository.login(username, password)) {
                is ApiResult.Success -> fetchDashboard()
                is ApiResult.Error -> _uiState.value = MainUiState.Error("Unable to sign in")
            }
        }
    }

    private suspend fun fetchDashboard() {
        when (val result = repository.fetchCurrentDashboard()) {
            is ApiResult.Success -> _uiState.value = MainUiState.Dashboard(result.data)
            is ApiResult.Error -> _uiState.value = MainUiState.Error(result.message)
        }
    }
}
