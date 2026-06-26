package com.crai.chromebook.api

import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Path

interface KioskoApi {

    /** Consulta el estado/préstamo de la Chromebook identificada por su código. */
    @GET("prestamos/api/kiosko/chromebook/{codigo}/estado/")
    suspend fun estado(
        @Path("codigo") codigo: String,
        @Header("X-KIOSKO-KEY") apiKey: String
    ): EstadoResponse
}
