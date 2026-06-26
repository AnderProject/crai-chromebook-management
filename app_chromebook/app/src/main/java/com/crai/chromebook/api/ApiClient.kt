package com.crai.chromebook.api

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient

/** Crea el cliente Retrofit apuntando a la URL del servidor configurada. */
object ApiClient {

    fun crear(baseUrl: String): KioskoApi {
        val url = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val http = OkHttpClient.Builder()
            .connectTimeout(8, TimeUnit.SECONDS)
            .readTimeout(8, TimeUnit.SECONDS)
            .build()
        return Retrofit.Builder()
            .baseUrl(url)
            .client(http)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(KioskoApi::class.java)
    }
}
