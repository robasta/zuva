package com.sunsynk.mobile.ui.dashboard

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.sunsynk.mobile.R
import com.sunsynk.mobile.shared.network.model.DashboardCurrentResponse
import com.sunsynk.mobile.shared.network.model.DashboardHistoryEntry
import com.sunsynk.mobile.shared.network.model.DashboardMetrics
import com.sunsynk.mobile.shared.network.model.DashboardStatus
import com.sunsynk.mobile.shared.network.model.TimeseriesPoint
import com.sunsynk.mobile.shared.network.model.WeatherForecastEntry
import com.sunsynk.mobile.ui.theme.SunsynkDashboardTheme
import java.util.Locale
import kotlin.math.max
import kotlin.math.roundToInt
import org.koin.androidx.compose.koinViewModel

@Composable
fun DashboardScreen(
    modifier: Modifier = Modifier,
    viewModel: DashboardViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsState()
    DashboardContent(
        modifier = modifier,
        state = state,
        onRefresh = viewModel::refresh
    )
}

@Composable
fun DashboardContent(
    modifier: Modifier = Modifier,
    state: DashboardUiState,
    onRefresh: () -> Unit
) {
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.error) {
        val message = state.error ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(message)
    }

    Scaffold(
        modifier = modifier,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { paddingValues ->
        DashboardBody(
            state = state,
            contentPadding = paddingValues,
            onRefresh = onRefresh
        )
    }
}

@Composable
private fun DashboardBody(
    state: DashboardUiState,
    contentPadding: PaddingValues,
    onRefresh: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(contentPadding)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        DashboardHeader(isRefreshing = state.isRefreshing, onRefresh = onRefresh)

        if (state.isOffline) {
            OfflineBanner()
        }

        when {
            state.isLoading -> LoadingSection()
            state.current != null -> MetricsSection(state.current.metrics)
            else -> EmptyState(onRefresh)
        }

        TimeseriesSection(points = state.timeseries)

        state.current?.let { current ->
            if (current.metrics.weatherCondition != null || current.metrics.temperature != null || current.weatherForecast.isNotEmpty()) {
                WeatherSection(metrics = current.metrics, forecast = current.weatherForecast)
            }
            StatusSection(status = current.status)
        }

        if (state.history.isNotEmpty()) {
            HistorySection(entries = state.history)
        }
    }
}

@Composable
private fun DashboardHeader(isRefreshing: Boolean, onRefresh: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(
                text = stringResource(id = R.string.dashboard_greeting),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = stringResource(id = R.string.dashboard_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(modifier = Modifier.weight(1f))
        Button(onClick = onRefresh, enabled = !isRefreshing) {
            Text(text = stringResource(id = R.string.dashboard_refresh))
        }
    }
}

@Composable
private fun OfflineBanner() {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.secondaryContainer
    ) {
        Text(
            text = stringResource(id = R.string.dashboard_offline_banner),
            modifier = Modifier.padding(12.dp),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSecondaryContainer
        )
    }
}

@Composable
private fun LoadingSection() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator()
        Text(
            text = stringResource(id = R.string.loading_message),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 16.dp)
        )
    }
}

@Composable
private fun MetricsSection(metrics: DashboardMetrics) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        tonalElevation = 2.dp,
        shape = MaterialTheme.shapes.medium
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            MetricRow(label = stringResource(id = R.string.metric_solar_power), value = "${metrics.solarPower} kW")
            MetricRow(label = stringResource(id = R.string.metric_consumption), value = "${metrics.consumption} kW")
            MetricRow(label = stringResource(id = R.string.metric_grid_power), value = "${metrics.gridPower} kW")
            MetricRow(label = stringResource(id = R.string.metric_battery_level), value = "${metrics.batteryLevel}%")
            metrics.weatherCondition?.let {
                MetricRow(label = stringResource(id = R.string.metric_weather), value = it)
            }
        }
    }
}

@Composable
private fun WeatherSection(metrics: DashboardMetrics, forecast: List<WeatherForecastEntry>) {
    val hasCurrentWeather = metrics.weatherCondition != null || metrics.temperature != null
    val hasForecast = forecast.isNotEmpty()
    if (!hasCurrentWeather && !hasForecast) return

    Surface(
        modifier = Modifier.fillMaxWidth(),
        tonalElevation = 2.dp,
        shape = MaterialTheme.shapes.medium
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = stringResource(id = R.string.dashboard_weather_title),
                style = MaterialTheme.typography.titleMedium
            )

            if (hasCurrentWeather) {
                CurrentWeatherRow(metrics = metrics)
            }

            if (hasForecast) {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(forecast.take(8)) { entry ->
                        WeatherForecastCard(entry = entry)
                    }
                }
            }
        }
    }
}

@Composable
private fun CurrentWeatherRow(metrics: DashboardMetrics) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = stringResource(id = R.string.dashboard_weather_current_label),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            metrics.weatherCondition?.let {
                Text(
                    text = formatCondition(it),
                    style = MaterialTheme.typography.bodyLarge
                )
            }
        }
        Spacer(modifier = Modifier.weight(1f))
        metrics.temperature?.let {
            Text(
                text = stringResource(id = R.string.dashboard_weather_temperature, it.roundToInt()),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun WeatherForecastCard(entry: WeatherForecastEntry) {
    Surface(
        tonalElevation = 1.dp,
        shape = MaterialTheme.shapes.small
    ) {
        Column(
            modifier = Modifier
                .width(88.dp)
                .padding(vertical = 12.dp, horizontal = 14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            val timeLabel = formatForecastTime(entry)
            if (timeLabel.isNotEmpty()) {
                Text(
                    text = timeLabel,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            entry.temperature?.let {
                Text(
                    text = stringResource(id = R.string.dashboard_weather_temperature, it.roundToInt()),
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold
                )
            }
            entry.condition?.let {
                Text(
                    text = formatCondition(it),
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
private fun MetricRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(text = label, style = MaterialTheme.typography.bodyMedium)
        Text(text = value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun StatusSection(status: DashboardStatus) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        tonalElevation = 2.dp,
        shape = MaterialTheme.shapes.medium
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(text = stringResource(id = R.string.dashboard_status_title), style = MaterialTheme.typography.titleMedium)
            Text(text = stringResource(id = R.string.dashboard_status_inverter, status.inverterStatus), style = MaterialTheme.typography.bodyMedium)
            Text(text = stringResource(id = R.string.dashboard_status_battery, status.batteryStatus), style = MaterialTheme.typography.bodyMedium)
            Text(text = stringResource(id = R.string.dashboard_status_grid, status.gridStatus), style = MaterialTheme.typography.bodyMedium)
            Text(
                text = stringResource(id = R.string.dashboard_status_updated, status.lastUpdate),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun TimeseriesSection(points: List<TimeseriesPoint>) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        tonalElevation = 2.dp,
        shape = MaterialTheme.shapes.medium
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(text = stringResource(id = R.string.dashboard_timeseries_title), style = MaterialTheme.typography.titleMedium)
            if (points.size < 2) {
                Text(
                    text = stringResource(id = R.string.dashboard_timeseries_empty),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                TimeseriesChart(points = points)
                TimeseriesLegend()
            }
        }
    }
}

@Composable
private fun TimeseriesChart(points: List<TimeseriesPoint>, modifier: Modifier = Modifier) {
    val maxValue = points.maxOf { max(it.generation, it.consumption) }.coerceAtLeast(1.0)
    val colorGeneration = MaterialTheme.colorScheme.primary
    val colorConsumption = MaterialTheme.colorScheme.tertiary
    val baselineColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.1f)

    Canvas(modifier = modifier.fillMaxWidth().height(200.dp)) {
        val chartHeight = size.height
        val chartWidth = size.width
        val stepX = if (points.size > 1) chartWidth / (points.size - 1) else chartWidth
        val yScale = chartHeight / maxValue.toFloat()

        // Baseline
        drawLine(
            color = baselineColor,
            start = Offset(0f, chartHeight),
            end = Offset(chartWidth, chartHeight),
            strokeWidth = 2f
        )

        fun buildPath(valueSelector: (TimeseriesPoint) -> Double): Path {
            val path = Path()
            points.forEachIndexed { index, point ->
                val x = index * stepX
                val y = chartHeight - (valueSelector(point).toFloat() * yScale)
                if (index == 0) {
                    path.moveTo(x, y)
                } else {
                    path.lineTo(x, y)
                }
            }
            return path
        }

        drawPath(
            path = buildPath { it.generation },
            color = colorGeneration,
            style = Stroke(width = 6f, cap = StrokeCap.Round)
        )

        drawPath(
            path = buildPath { it.consumption },
            color = colorConsumption,
            style = Stroke(width = 6f, cap = StrokeCap.Round)
        )
    }
}

@Composable
private fun TimeseriesLegend() {
    Row(
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        LegendItem(color = MaterialTheme.colorScheme.primary, label = stringResource(id = R.string.dashboard_timeseries_generation))
        LegendItem(color = MaterialTheme.colorScheme.tertiary, label = stringResource(id = R.string.dashboard_timeseries_consumption))
    }
}

@Composable
private fun LegendItem(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            modifier = Modifier
                .width(24.dp)
                .height(12.dp)
                .background(color = color, shape = MaterialTheme.shapes.small)
        )
        Text(text = label, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun HistorySection(entries: List<DashboardHistoryEntry>) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(text = stringResource(id = R.string.dashboard_history_title), style = MaterialTheme.typography.titleMedium)
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 320.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(entries) { entry ->
                Surface(
                    tonalElevation = 2.dp,
                    shape = MaterialTheme.shapes.small,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = entry.timestamp, style = MaterialTheme.typography.bodySmall)
                        Text(text = stringResource(id = R.string.dashboard_history_generation, entry.solarPower), style = MaterialTheme.typography.bodyMedium)
                        Text(text = stringResource(id = R.string.dashboard_history_consumption, entry.consumption), style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}

@Composable
private fun EmptyState(onRefresh: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = stringResource(id = R.string.dashboard_empty_title), style = MaterialTheme.typography.titleMedium)
        Text(
            text = stringResource(id = R.string.dashboard_empty_message),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 8.dp),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Button(onClick = onRefresh, modifier = Modifier.padding(top = 16.dp)) {
            Text(text = stringResource(id = R.string.dashboard_refresh))
        }
    }
}

private fun formatCondition(value: String): String {
    val normalized = value.replace('_', ' ')
    return normalized.replaceFirstChar { char ->
        if (char.isLowerCase()) char.titlecase(Locale.getDefault()) else char.toString()
    }
}

private fun formatForecastTime(entry: WeatherForecastEntry): String {
    val raw = entry.time ?: entry.resolvedTimestamp ?: return ""
    val timePortion = raw.split('T').lastOrNull() ?: raw
    return if (timePortion.length >= 5) timePortion.substring(0, 5) else timePortion
}

@Preview
@Composable
private fun DashboardContentPreview() {
    SunsynkDashboardTheme {
        DashboardContent(
            state = DashboardUiState(
                isLoading = false,
                isRefreshing = false,
                isOffline = true,
                current = DashboardCurrentResponse(
                    metrics = DashboardMetrics(
                        timestamp = "2025-11-18T08:00:00Z",
                        solarPower = 3.4,
                        batteryLevel = 78.0,
                        gridPower = -1.2,
                        consumption = 2.1,
                        weatherCondition = "Sunny",
                        temperature = 24.0
                    ),
                    status = DashboardStatus(
                        online = true,
                        lastUpdate = "2025-11-18T08:05:00Z",
                        inverterStatus = "Active",
                        batteryStatus = "Charging",
                        gridStatus = "Stable"
                    ),
                    weatherForecast = listOf(
                        WeatherForecastEntry(time = "09:00", condition = "sunny", temperature = 25.0),
                        WeatherForecastEntry(time = "12:00", condition = "clouds", temperature = 26.0)
                    )
                ),
                history = listOf(
                    DashboardHistoryEntry(
                        timestamp = "2025-11-18T07:00:00Z",
                        solarPower = 2.4,
                        batteryLevel = 70.0,
                        gridPower = -0.5,
                        consumption = 2.0,
                        batteryPower = null
                    )
                ),
                timeseries = listOf(
                    TimeseriesPoint("t1", 1.0, 1.2, 50.0, 60.0),
                    TimeseriesPoint("t2", 1.6, 1.4, 52.0, 61.0),
                    TimeseriesPoint("t3", 2.0, 1.8, 53.0, 62.0)
                ),
                error = null
            ),
            onRefresh = {}
        )
    }
}
