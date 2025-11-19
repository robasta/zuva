package com.sunsynk.mobile.notifications

import com.sunsynk.mobile.shared.network.model.AlertDto
import com.sunsynk.mobile.shared.network.model.AlertNotificationPayload
import com.sunsynk.mobile.shared.network.model.AlertStatus

internal fun AlertNotificationPayload.toDto(): AlertDto = AlertDto(
    id = id,
    title = title,
    message = message,
    severity = severity,
    status = AlertStatus.ACTIVE,
    category = category,
    timestamp = timestamp,
    acknowledgedAt = null,
    resolvedAt = null
)
