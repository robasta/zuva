package com.sunsynk.mobile.shared.network

import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds

data class SunsynkApiConfig(
    val baseUrl: String = "http://10.0.2.2:8000/api",
    val websocketUrl: String = "ws://10.0.2.2:8000/ws/dashboard",
    val connectTimeout: Duration = 30.seconds,
    val requestTimeout: Duration = 30.seconds
)
