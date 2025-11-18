package com.sunsynk.mobile.shared.network

import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds

data class SunsynkApiConfig(
    val baseUrl: String = "http://localhost:8000/api",
    val websocketUrl: String = "ws://localhost:8000/ws/dashboard",
    val connectTimeout: Duration = 30.seconds,
    val requestTimeout: Duration = 30.seconds
)
