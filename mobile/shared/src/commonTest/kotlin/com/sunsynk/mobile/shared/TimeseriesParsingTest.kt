package com.sunsynk.mobile.shared

import com.sunsynk.mobile.shared.network.model.TimeseriesResponse
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TimeseriesParsingTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `parses timeseries payload with unique timestamps`() {
        val payload = """
            {
              "success": true,
              "data": [
                {
                  "timestamp": "2025-11-18T06:00:00.000000Z",
                  "generation": 1.92,
                  "consumption": 2.35,
                  "battery_soc": 73.4,
                  "battery_level": 73.4
                },
                {
                  "timestamp": "2025-11-18T06:15:00.000000Z",
                  "generation": 2.10,
                  "consumption": 2.40,
                  "battery_soc": 74.0,
                  "battery_level": 74.0
                }
              ],
              "source": "influxdb",
              "count": 2,
              "resolution": "15m",
              "time_span": "24h"
            }
        """.trimIndent()

        val result = json.decodeFromString<TimeseriesResponse>(payload)

        assertTrue(result.success)
        assertEquals(2, result.data.size)
        assertEquals("2025-11-18T06:15:00.000000Z", result.data.last().timestamp)
        assertEquals(74.0, result.data.last().batterySoc)
    }
}
