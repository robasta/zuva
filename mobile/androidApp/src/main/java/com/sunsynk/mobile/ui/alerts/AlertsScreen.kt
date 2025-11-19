package com.sunsynk.mobile.ui.alerts

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.sunsynk.mobile.R
import com.sunsynk.mobile.data.local.AlertEntity
import com.sunsynk.mobile.shared.network.model.AlertSeverity
import com.sunsynk.mobile.shared.network.model.AlertStatus
import org.koin.androidx.compose.koinViewModel

@Composable
fun AlertsScreen(
    modifier: Modifier = Modifier,
    viewModel: AlertsViewModel = koinViewModel()
) {
    val alerts by viewModel.alerts.collectAsState()
    val uiState by viewModel.uiState.collectAsState()

    AlertsContent(
        modifier = modifier,
        alerts = alerts,
        state = uiState,
        onRefresh = viewModel::refresh,
        onAcknowledge = viewModel::acknowledge,
        onResolve = viewModel::resolve
    )
}

@Composable
fun AlertsContent(
    modifier: Modifier = Modifier,
    alerts: List<AlertEntity>,
    state: AlertsUiState,
    onRefresh: () -> Unit,
    onAcknowledge: (AlertEntity) -> Unit,
    onResolve: (AlertEntity) -> Unit
) {
    val selectedAlert = remember { mutableStateOf<AlertEntity?>(null) }
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        AlertsHeader(onRefresh = onRefresh, isRefreshing = state.isRefreshing)

        state.error?.let { message ->
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.errorContainer,
                shape = MaterialTheme.shapes.small
            ) {
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.padding(12.dp)
                )
            }
        }

        when {
            state.isLoading -> LoadingSection()
            alerts.isEmpty() -> EmptyState(onRefresh = onRefresh)
            else -> AlertsList(alerts = alerts, onSelect = { selectedAlert.value = it })
        }
    }

    selectedAlert.value?.let { alert ->
        AlertDetailDialog(
            alert = alert,
            onDismiss = { selectedAlert.value = null },
            onAcknowledge = {
                onAcknowledge(alert)
                selectedAlert.value = null
            },
            onResolve = {
                onResolve(alert)
                selectedAlert.value = null
            }
        )
    }
}

@Composable
private fun AlertsHeader(onRefresh: () -> Unit, isRefreshing: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(imageVector = Icons.Default.Notifications, contentDescription = null)
        Text(
            text = stringResource(id = R.string.alerts_title),
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.padding(start = 8.dp)
        )
        Spacer(modifier = Modifier.weight(1f))
        Button(onClick = onRefresh, enabled = !isRefreshing) {
            Text(text = stringResource(id = R.string.alerts_refresh))
        }
    }
}

@Composable
private fun LoadingSection() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 200.dp),
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator()
    }
}

@Composable
private fun AlertsList(alerts: List<AlertEntity>, onSelect: (AlertEntity) -> Unit) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        items(alerts, key = { it.id }) { alert ->
            AlertListItem(alert = alert, onSelect = onSelect)
        }
    }
}

@Composable
private fun AlertListItem(alert: AlertEntity, onSelect: (AlertEntity) -> Unit) {
    val severityColor = severityColor(alert.severity)

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onSelect(alert) },
        tonalElevation = 2.dp,
        shape = MaterialTheme.shapes.medium
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .background(color = severityColor, shape = MaterialTheme.shapes.small)
                        .heightIn(min = 8.dp)
                        .padding(horizontal = 8.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = alert.severity.name.lowercase().replaceFirstChar { it.titlecase() },
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White
                    )
                }
                Spacer(modifier = Modifier.weight(1f))
                StatusBadge(status = alert.status)
            }
            Text(
                text = alert.title,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 8.dp)
            )
            Text(
                text = alert.message,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 4.dp),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = alert.timestamp,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp)
            )
        }
    }
}

@Composable
private fun StatusBadge(status: AlertStatus) {
    val (label, color) = when (status) {
        AlertStatus.ACTIVE -> stringResource(id = R.string.alert_status_active) to MaterialTheme.colorScheme.error
        AlertStatus.ACKNOWLEDGED -> stringResource(id = R.string.alert_status_acknowledged) to MaterialTheme.colorScheme.tertiary
        AlertStatus.RESOLVED -> stringResource(id = R.string.alert_status_resolved) to MaterialTheme.colorScheme.primary
    }
    Surface(
        color = color.copy(alpha = 0.15f),
        shape = MaterialTheme.shapes.small
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = color,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun AlertDetailDialog(
    alert: AlertEntity,
    onDismiss: () -> Unit,
    onAcknowledge: () -> Unit,
    onResolve: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (alert.status == AlertStatus.ACTIVE) {
                    TextButton(onClick = onAcknowledge) {
                        Text(text = stringResource(id = R.string.alert_action_acknowledge))
                    }
                }
                if (alert.status != AlertStatus.RESOLVED) {
                    TextButton(onClick = onResolve) {
                        Text(text = stringResource(id = R.string.alert_action_resolve))
                    }
                }
                TextButton(onClick = onDismiss) {
                    Text(text = stringResource(id = R.string.alert_action_close))
                }
            }
        },
        title = { Text(text = alert.title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(text = alert.message)
                Text(text = stringResource(id = R.string.alert_detail_category, alert.category))
                Text(text = stringResource(id = R.string.alert_detail_timestamp, alert.timestamp))
                alert.acknowledgedAt?.let {
                    Text(text = stringResource(id = R.string.alert_detail_acknowledged, it))
                }
                alert.resolvedAt?.let {
                    Text(text = stringResource(id = R.string.alert_detail_resolved, it))
                }
            }
        }
    )
}

@Composable
private fun EmptyState(onRefresh: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 200.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = stringResource(id = R.string.alerts_empty_title), style = MaterialTheme.typography.titleMedium)
        Text(
            text = stringResource(id = R.string.alerts_empty_message),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 8.dp),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Button(onClick = onRefresh, modifier = Modifier.padding(top = 16.dp)) {
            Text(text = stringResource(id = R.string.alerts_refresh))
        }
    }
}

@Composable
private fun severityColor(severity: AlertSeverity): Color = when (severity) {
    AlertSeverity.CRITICAL -> MaterialTheme.colorScheme.error
    AlertSeverity.HIGH -> MaterialTheme.colorScheme.tertiary
    AlertSeverity.MEDIUM -> MaterialTheme.colorScheme.primary
    AlertSeverity.LOW -> MaterialTheme.colorScheme.secondary
}