package com.crai.chromebook.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update

@Dao
interface ReservaDao {

    @Insert
    suspend fun insertar(reserva: Reserva): Long

    @Update
    suspend fun actualizar(reserva: Reserva)

    /** La reserva activa actual (debería haber solo una en la Chromebook). */
    @Query("SELECT * FROM reservas WHERE estado = 'ACTIVA' ORDER BY inicio DESC LIMIT 1")
    suspend fun reservaActiva(): Reserva?

    /** Reservas que aún no se han enviado al backend (Fase 4: sync). */
    @Query("SELECT * FROM reservas WHERE sincronizada = 0")
    suspend fun noSincronizadas(): List<Reserva>

    @Query("SELECT * FROM reservas ORDER BY inicio DESC")
    suspend fun todas(): List<Reserva>
}
