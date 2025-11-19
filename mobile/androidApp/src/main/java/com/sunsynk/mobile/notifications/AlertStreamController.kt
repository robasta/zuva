package com.sunsynk.mobile.notifications

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

class AlertStreamController(private val context: Context) {

    fun start() {
        ContextCompat.startForegroundService(context, Intent(context, AlertStreamService::class.java))
    }

    fun stop() {
        context.stopService(Intent(context, AlertStreamService::class.java))
    }
}
