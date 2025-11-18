package com.sunsynk.mobile.shared.network

import io.ktor.client.HttpClient

expect fun providePlatformHttpClient(config: SunsynkApiConfig): HttpClient
