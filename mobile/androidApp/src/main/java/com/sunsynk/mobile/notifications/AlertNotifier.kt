package com.sunsynk.mobile.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.graphics.Color
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.sunsynk.mobile.R
import com.sunsynk.mobile.shared.network.model.AlertNotification
import com.sunsynk.mobile.shared.network.model.AlertSeverity

interface AlertNotifier {
    fun notify(notification: AlertNotification)
}

class SystemAlertNotifier(private val context: Context) : AlertNotifier {

    private val manager: NotificationManagerCompat = NotificationManagerCompat.from(context)

    init {
        createChannels()
    }

    override fun notify(notification: AlertNotification) {
        val payload = notification.data
        val channelId = channelForSeverity(payload.severity)
        val builder = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(payload.title)
            .setContentText(payload.message)
            .setPriority(priorityForSeverity(payload.severity))
            .setAutoCancel(true)

        manager.notify(payload.id.hashCode(), builder.build())
    }

    private fun channelForSeverity(severity: AlertSeverity): String = when (severity) {
        AlertSeverity.CRITICAL -> CHANNEL_CRITICAL
        AlertSeverity.HIGH -> CHANNEL_HIGH
        AlertSeverity.MEDIUM -> CHANNEL_MEDIUM
        AlertSeverity.LOW -> CHANNEL_LOW
    }

    private fun priorityForSeverity(severity: AlertSeverity): Int = when (severity) {
        AlertSeverity.CRITICAL, AlertSeverity.HIGH -> NotificationCompat.PRIORITY_HIGH
        AlertSeverity.MEDIUM -> NotificationCompat.PRIORITY_DEFAULT
        AlertSeverity.LOW -> NotificationCompat.PRIORITY_LOW
    }

    private fun createChannels() {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channels = listOf(
            NotificationChannel(
                CHANNEL_CRITICAL,
                context.getString(R.string.channel_alerts_critical),
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                enableLights(true)
                lightColor = Color.RED
                enableVibration(true)
            },
            NotificationChannel(
                CHANNEL_HIGH,
                context.getString(R.string.channel_alerts_high),
                NotificationManager.IMPORTANCE_HIGH
            ),
            NotificationChannel(
                CHANNEL_MEDIUM,
                context.getString(R.string.channel_alerts_medium),
                NotificationManager.IMPORTANCE_DEFAULT
            ),
            NotificationChannel(
                CHANNEL_LOW,
                context.getString(R.string.channel_alerts_low),
                NotificationManager.IMPORTANCE_LOW
            )
        )
        channels.forEach { manager.createNotificationChannel(it) }
    }

    companion object {
        private const val CHANNEL_CRITICAL = "alerts_critical"
        private const val CHANNEL_HIGH = "alerts_high"
        private const val CHANNEL_MEDIUM = "alerts_medium"
        private const val CHANNEL_LOW = "alerts_low"
    }
}
