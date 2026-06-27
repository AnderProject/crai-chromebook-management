package com.crai.chromebook.api

/** Respuesta de GET .../api/kiosko/chromebook/{codigo}/estado/ */
data class EstadoResponse(
    val success: Boolean = false,
    val codigo: String? = null,
    val estado_equipo: String? = null,
    val prestamo: PrestamoDto? = null
)

/** Préstamo activo devuelto por el servidor (null si la Chromebook está libre). */
data class PrestamoDto(
    val id: Long = 0,
    val estudiante: String = "",
    val cedula: String = "",
    val estado: String = "",
    val bloqueado: Boolean = false,
    val foto_url: String? = null,
    val inicio_ms: Long = 0,
    val fin_ms: Long = 0
)
