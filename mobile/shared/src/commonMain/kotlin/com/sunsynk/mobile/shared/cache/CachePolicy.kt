package com.sunsynk.mobile.shared.cache

import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlinx.datetime.plus
import kotlinx.datetime.minus
import kotlin.time.Duration
import kotlin.time.Duration.Companion.hours

object CachePolicy {
    val DEFAULT_TTL: Duration = 24.hours
}

fun <T> CachedValue<T>.isFresh(ttl: Duration = CachePolicy.DEFAULT_TTL): Boolean =
    timestamp.plus(ttl) >= Clock.System.now()

fun expirationThreshold(ttl: Duration = CachePolicy.DEFAULT_TTL): Instant =
    Clock.System.now().minus(ttl)
