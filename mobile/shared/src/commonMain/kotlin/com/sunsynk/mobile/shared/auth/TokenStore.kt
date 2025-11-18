package com.sunsynk.mobile.shared.auth

interface TokenStore {
    suspend fun readToken(): String?
    suspend fun writeToken(token: String?)
}

class InMemoryTokenStore : TokenStore {
    private var cachedToken: String? = null

    override suspend fun readToken(): String? = cachedToken

    override suspend fun writeToken(token: String?) {
        cachedToken = token
    }
}
