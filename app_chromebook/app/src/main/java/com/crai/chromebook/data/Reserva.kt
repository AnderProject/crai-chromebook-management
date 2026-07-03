package com.crai.chromebook.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/** Estado de una reserva local (espejo de la lógica del backend Django). */
enum class EstadoReserva { ACTIVA, DEVUELTA, VENCIDA }

/**
 * Reserva guardada en la caché local de la Chromebook.
 *
 * El inicio se guarda como epoch millis, así el tiempo restante se calcula
 * siempre contra el reloj actual: aunque la app se cierre o reinicie, al volver
 * a abrir se recupera el estado real (no se "pausa" el contador).
 */
@Entity(tableName = "reservas")
data class Reserva(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val cedula: String,
    val nombre: String,
    val inicio: Long,
    val duracionMinutos: Int,
    val estado: EstadoReserva = EstadoReserva.ACTIVA,
    val sincronizada: Boolean = false
) {
    /** Sesión sin límite de tiempo (no vence por reloj). */
    val ilimitada: Boolean get() = duracionMinutos <= 0

    val finPrevisto: Long
        get() = if (ilimitada) Long.MAX_VALUE else inicio + duracionMinutos * 60_000L

    /** Milisegundos que faltan para vencer (0 si ya venció; "infinito" si es ilimitada). */
    fun restanteMillis(ahora: Long = System.currentTimeMillis()): Long =
        if (ilimitada) Long.MAX_VALUE else (finPrevisto - ahora).coerceAtLeast(0L)
}
