package com.crai.chromebook.data

/** Punto único de acceso a las reservas (oculta el DAO al resto de la app). */
class ReservaRepository(private val dao: ReservaDao) {

    suspend fun activa(): Reserva? = dao.reservaActiva()

    suspend fun iniciar(cedula: String, nombre: String, duracionMin: Int): Reserva {
        val reserva = Reserva(
            cedula = cedula,
            nombre = nombre,
            inicio = System.currentTimeMillis(),
            duracionMinutos = duracionMin
        )
        val id = dao.insertar(reserva)
        return reserva.copy(id = id)
    }

    suspend fun devolver(reserva: Reserva) {
        dao.actualizar(reserva.copy(estado = EstadoReserva.DEVUELTA))
    }

    suspend fun vencer(reserva: Reserva) {
        dao.actualizar(reserva.copy(estado = EstadoReserva.VENCIDA))
    }
}
