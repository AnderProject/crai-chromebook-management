package com.crai.chromebook.data

import androidx.room.TypeConverter

/** Convierte el enum de estado a texto para almacenarlo en SQLite. */
class Converters {
    @TypeConverter
    fun fromEstado(estado: EstadoReserva): String = estado.name

    @TypeConverter
    fun toEstado(valor: String): EstadoReserva = EstadoReserva.valueOf(valor)
}
