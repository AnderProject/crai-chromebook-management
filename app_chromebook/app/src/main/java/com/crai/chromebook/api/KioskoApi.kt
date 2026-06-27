package com.crai.chromebook.api

import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

interface KioskoApi {

    /** Consulta el estado/préstamo de la Chromebook identificada por su código. */
    @GET("prestamos/api/kiosko/chromebook/{codigo}/estado/")
    suspend fun estado(
        @Path("codigo") codigo: String,
        @Header("X-KIOSKO-KEY") apiKey: String
    ): EstadoResponse

    /** Avisa que el personal desbloqueó con PIN: limpia el flag de bloqueo remoto. */
    @POST("prestamos/api/kiosko/chromebook/{codigo}/desbloquear/")
    suspend fun desbloquear(
        @Path("codigo") codigo: String,
        @Header("X-KIOSKO-KEY") apiKey: String
    ): EstadoResponse
}
