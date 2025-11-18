package com.sunsynk.mobile

import android.app.Application
import com.sunsynk.mobile.di.androidModule
import com.sunsynk.mobile.shared.di.sharedModule
import org.koin.android.ext.koin.androidContext
import org.koin.android.ext.koin.androidLogger
import org.koin.core.logger.Level
import org.koin.core.context.startKoin

class SunsynkDashboardApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidLogger(Level.ERROR)
            androidContext(this@SunsynkDashboardApplication)
            modules(sharedModule, androidModule)
        }
    }
}
