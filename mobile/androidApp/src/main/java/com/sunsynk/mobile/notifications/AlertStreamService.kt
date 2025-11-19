package com.sunsynk.mobile.notifications

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import com.sunsynk.mobile.MainActivity
import com.sunsynk.mobile.R
import com.sunsynk.mobile.data.local.AlertLocalDataSource
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import com.sunsynk.mobile.shared.util.ApiResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import org.koin.android.ext.android.inject

class AlertStreamService : LifecycleService() {

    private val repository by inject<SunsynkRepository>()
    private val notifier by inject<AlertNotifier>()
    private val localDataSource by inject<AlertLocalDataSource>()

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var streamingJob: Job? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(FOREGROUND_NOTIFICATION_ID, persistentNotification())
        if (streamingJob?.isActive != true) {
            streamingJob = serviceScope.launch {
                repository.observeAlertNotifications().collect { result ->
                    when (result) {
                        is ApiResult.Success -> {
                            notifier.notify(result.data)
                            localDataSource.upsert(result.data.data.toDto())
                        }
                        is ApiResult.Error -> {
                            // Keep service alive; errors are surfaced via notifications when ViewModel collects.
                        }
                    }
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        streamingJob?.cancel()
        serviceScope.cancel()
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    override fun onBind(intent: Intent): IBinder? = super.onBind(intent)

    private fun persistentNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(getString(R.string.notification_alert_service_title))
            .setContentText(getString(R.string.notification_alert_service_body))
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .setCategory(Notification.CATEGORY_SERVICE)
            .build()
    }

    private fun createChannel() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.channel_alert_service),
            NotificationManager.IMPORTANCE_MIN
        )
        manager.createNotificationChannel(channel)
    }

    companion object {
        private const val CHANNEL_ID = "alert_stream_service"
        private const val FOREGROUND_NOTIFICATION_ID = 1001
    }
}
