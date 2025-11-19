package com.sunsynk.mobile.shared.cache

import kotlinx.datetime.Instant

data class CachedValue<T>(
    val data: T,
    val timestamp: Instant
)
