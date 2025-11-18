package com.sunsynk.mobile.shared.network

import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import java.util.concurrent.TimeUnit

actual fun providePlatformHttpClient(config: SunsynkApiConfig): HttpClient = HttpClient(OkHttp) {
    install(HttpTimeout) {
        requestTimeoutMillis = config.requestTimeout.inWholeMilliseconds
        connectTimeoutMillis = config.connectTimeout.inWholeMilliseconds
        socketTimeoutMillis = config.requestTimeout.inWholeMilliseconds
    }

    install(ContentNegotiation) {
        json(
            Json {
                ignoreUnknownKeys = true
                isLenient = true
                encodeDefaults = true
            }
        )
    }

    install(Logging) {
        level = LogLevel.INFO
    }

    engine {
        config {
            readTimeout(config.requestTimeout.inWholeMilliseconds, TimeUnit.MILLISECONDS)
            connectTimeout(config.connectTimeout.inWholeMilliseconds, TimeUnit.MILLISECONDS)
        }
    }
}
