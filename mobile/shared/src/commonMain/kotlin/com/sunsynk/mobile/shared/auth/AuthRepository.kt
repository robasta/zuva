package com.sunsynk.mobile.shared.auth

import com.sunsynk.mobile.shared.network.model.LoginResponse
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import com.sunsynk.mobile.shared.util.ApiResult
import com.sunsynk.mobile.shared.util.ApiResult.Error
import com.sunsynk.mobile.shared.util.ApiResult.Success

class AuthRepository(
    private val repository: SunsynkRepository,
    private val tokenStore: TokenStore
) {
    suspend fun login(username: String, password: String): ApiResult<LoginResponse> {
        return when (val result = repository.login(username, password)) {
            is Success -> {
                tokenStore.writeToken(result.data.accessToken)
                result
            }
            is Error -> result
        }
    }

    suspend fun logout() {
        tokenStore.writeToken(null)
    }

    suspend fun currentToken(): String? = tokenStore.readToken()
}
