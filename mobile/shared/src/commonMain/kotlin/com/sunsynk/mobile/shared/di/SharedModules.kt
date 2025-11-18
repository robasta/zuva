package com.sunsynk.mobile.shared.di

import com.sunsynk.mobile.shared.auth.AuthRepository
import com.sunsynk.mobile.shared.auth.InMemoryTokenStore
import com.sunsynk.mobile.shared.auth.TokenStore
import com.sunsynk.mobile.shared.network.SunsynkApiClient
import com.sunsynk.mobile.shared.network.SunsynkApiConfig
import com.sunsynk.mobile.shared.network.providePlatformHttpClient
import com.sunsynk.mobile.shared.repository.SunsynkRepository
import org.koin.core.module.Module
import org.koin.dsl.module

val sharedModule: Module = module {
    single { SunsynkApiConfig() }
    single<TokenStore> { InMemoryTokenStore() }
    single { providePlatformHttpClient(get()) }
    single {
        val tokenStore: TokenStore = get()
        SunsynkApiClient(
            httpClient = get(),
            config = get(),
            tokenProvider = { tokenStore.readToken() }
        )
    }
    single { AuthRepository(repository = get(), tokenStore = get()) }
    single { SunsynkRepository(get()) }
}
