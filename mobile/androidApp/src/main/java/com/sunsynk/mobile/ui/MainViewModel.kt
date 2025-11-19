package com.sunsynk.mobile.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sunsynk.mobile.notifications.AlertStreamController
import com.sunsynk.mobile.shared.auth.AuthRepository
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainViewModel(
    private val authRepository: AuthRepository,
    private val alertStreamController: AlertStreamController
) : ViewModel() {

    private val _uiState = MutableStateFlow<MainUiState>(MainUiState.Loading)
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()

    init {
        bootstrap()
    }

    fun login(username: String, password: String) {
        _uiState.value = MainUiState.Loading
        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) { authRepository.login(username, password) }
            when (result) {
                is ApiResult.Success -> {
                    alertStreamController.start()
                    _uiState.value = MainUiState.Authenticated
                }
                is ApiResult.Error -> _uiState.value = MainUiState.Error(result.message)
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            withContext(Dispatchers.IO) { authRepository.logout() }
            alertStreamController.stop()
            _uiState.value = MainUiState.Unauthenticated
        }
    }

    private fun bootstrap() {
        viewModelScope.launch {
            val token = withContext(Dispatchers.IO) { authRepository.currentToken() }
            if (token == null) {
                _uiState.value = MainUiState.Unauthenticated
            } else {
                alertStreamController.start()
                _uiState.value = MainUiState.Authenticated
            }
        }
    }
}

sealed interface MainUiState {
    data object Loading : MainUiState
    data object Unauthenticated : MainUiState
    data object Authenticated : MainUiState
    data class Error(val message: String) : MainUiState
}
