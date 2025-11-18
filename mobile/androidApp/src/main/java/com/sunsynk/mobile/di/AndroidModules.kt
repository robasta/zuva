package com.sunsynk.mobile.di

import com.sunsynk.mobile.ui.MainViewModel
import org.koin.androidx.viewmodel.dsl.viewModel
import org.koin.dsl.module

val androidModule = module {
    viewModel { MainViewModel(authRepository = get(), repository = get()) }
}
