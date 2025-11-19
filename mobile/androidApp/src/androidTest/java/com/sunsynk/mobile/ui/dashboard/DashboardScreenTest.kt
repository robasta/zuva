package com.sunsynk.mobile.ui.dashboard

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sunsynk.mobile.R
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryEntry
import com.sunsynk.mobile.shared.network.model.DashboardMetrics
import com.sunsynk.mobile.shared.network.model.DashboardStatus
import com.sunsynk.mobile.shared.network.model.WeatherForecastEntry
import com.sunsynk.mobile.ui.theme.SunsynkDashboardTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DashboardScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun offlineBannerVisibleWhenOffline() {
        val state = DashboardUiState(
            isLoading = false,
            current = sampleCurrent(),
            history = emptyList(),
            timeseries = emptyList(),
            error = null,
            isOffline = true
        )

        composeTestRule.setContent {
            SunsynkDashboardTheme {
                DashboardContent(
                    state = state,
                    onRefresh = {}
                )
            }
        }

        val offlineText = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.dashboard_offline_banner)
        composeTestRule.onNodeWithText(offlineText).assertIsDisplayed()
    }

    @Test
    fun historyEntriesRendered() {
        val state = DashboardUiState(
            isLoading = false,
            current = sampleCurrent(),
            history = listOf(
                DashboardHistoryEntry(
                    timestamp = "2025-11-18T08:00:00Z",
                    solarPower = 3.0,
                    batteryLevel = 75.0,
                    gridPower = -1.0,
                    consumption = 2.5,
                    batteryPower = null
                )
            ),
            timeseries = emptyList(),
            error = null,
            isOffline = false
        )

        composeTestRule.setContent {
            SunsynkDashboardTheme {
                DashboardContent(
                    state = state,
                    onRefresh = {}
                )
            }
        }

        val historyTitle = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.dashboard_history_title)
        composeTestRule.onNodeWithText(historyTitle).assertIsDisplayed()
        composeTestRule.onNodeWithText("2025-11-18T08:00:00Z").assertIsDisplayed()
    }

    @Test
    fun weatherSectionDisplaysForecast() {
        val forecastTime = "09:00"
        val state = DashboardUiState(
            isLoading = false,
            current = sampleCurrent().copy(
                weatherForecast = listOf(
                    WeatherForecastEntry(time = forecastTime, condition = "sunny", temperature = 26.0)
                )
            ),
            history = emptyList(),
            timeseries = emptyList(),
            error = null,
            isOffline = false
        )

        composeTestRule.setContent {
            SunsynkDashboardTheme {
                DashboardContent(
                    state = state,
                    onRefresh = {}
                )
            }
        }

        val weatherTitle = InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.dashboard_weather_title)
        composeTestRule.onNodeWithText(weatherTitle).assertIsDisplayed()
        composeTestRule.onNodeWithText(forecastTime).assertIsDisplayed()
    }

    private fun sampleCurrent(): DashboardCurrentResponse = DashboardCurrentResponse(
        metrics = DashboardMetrics(
            timestamp = "2025-11-18T08:00:00Z",
            solarPower = 4.2,
            batteryLevel = 80.0,
            gridPower = -1.5,
            consumption = 2.7,
            weatherCondition = "Sunny",
            temperature = 25.0
        ),
        status = DashboardStatus(
            online = true,
            lastUpdate = "2025-11-18T08:05:00Z",
            inverterStatus = "Active",
            batteryStatus = "Charging",
            gridStatus = "Stable"
        ),
        weatherForecast = emptyList()
    )
}
