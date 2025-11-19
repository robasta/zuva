package com.sunsynk.mobile.di

import androidx.room.Room
import com.sunsynk.mobile.data.EncryptedTokenStore
import com.sunsynk.mobile.data.local.AlertLocalDataSource
import com.sunsynk.mobile.data.local.DashboardCacheDao
import com.sunsynk.mobile.data.local.DashboardCacheImpl
import com.sunsynk.mobile.data.local.SunsynkDatabase
import com.sunsynk.mobile.notifications.AlertNotifier
import com.sunsynk.mobile.notifications.AlertStreamController
import com.sunsynk.mobile.notifications.SystemAlertNotifier
import com.sunsynk.mobile.shared.auth.TokenStore
import com.sunsynk.mobile.shared.cache.DashboardCache
import com.sunsynk.mobile.ui.MainViewModel
import com.sunsynk.mobile.ui.alerts.AlertsViewModel
import com.sunsynk.mobile.ui.dashboard.DashboardViewModel
import org.koin.androidx.viewmodel.dsl.viewModel
import org.koin.dsl.module

val androidModule = module {
    single<TokenStore> { EncryptedTokenStore(get()) }
    single {
        Room.databaseBuilder(get(), SunsynkDatabase::class.java, SunsynkDatabase.NAME)
            .fallbackToDestructiveMigration()
            .build()
    }
    single { get<SunsynkDatabase>().alertDao() }
    single<DashboardCacheDao> { get<SunsynkDatabase>().dashboardCacheDao() }
    single { AlertLocalDataSource(get()) }
    single<AlertNotifier> { SystemAlertNotifier(get()) }
    single<DashboardCache> { DashboardCacheImpl(get()) }
    single { AlertStreamController(get()) }

    viewModel { MainViewModel(authRepository = get(), alertStreamController = get()) }
    viewModel { DashboardViewModel(repository = get()) }
    viewModel { AlertsViewModel(repository = get(), localDataSource = get()) }
}
