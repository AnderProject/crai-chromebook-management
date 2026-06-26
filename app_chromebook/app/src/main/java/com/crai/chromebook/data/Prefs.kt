package com.crai.chromebook.data

import android.content.Context

/**
 * Configuración local del kiosko (editable por el personal del CRAI).
 *
 * OJO (placeholders de tesis): el PIN por defecto es "2468". Cámbialo en
 * producción desde la pantalla de configuración (botón ⚙ en el login).
 */
class Prefs(context: Context) {

    private val sp = context.getSharedPreferences("crai_kiosko", Context.MODE_PRIVATE)

    var duracionMinutos: Int
        get() = sp.getInt("duracion", 60)
        set(v) = sp.edit().putInt("duracion", v).apply()

    var pinStaff: String
        get() = sp.getString("pin", "2468") ?: "2468"
        set(v) = sp.edit().putString("pin", v).apply()

    // ---- Modo servidor (Fase 4: autoconfiguración desde Django) ----

    /** URL base del servidor Django, ej. http://192.168.100.7:8000/ */
    var servidorUrl: String
        get() = sp.getString("servidor_url", "") ?: ""
        set(v) = sp.edit().putString("servidor_url", v.trim()).apply()

    /** Código de inventario de ESTA Chromebook, ej. CB-005. */
    var codigoEquipo: String
        get() = sp.getString("codigo_equipo", "") ?: ""
        set(v) = sp.edit().putString("codigo_equipo", v.trim()).apply()

    /** Clave compartida que se envía en el header X-KIOSKO-KEY. */
    var apiKey: String
        get() = sp.getString("api_key", "clave-kiosko-dev") ?: "clave-kiosko-dev"
        set(v) = sp.edit().putString("api_key", v.trim()).apply()

    /** Hay modo automático si el equipo tiene servidor + código configurados. */
    val modoAuto: Boolean
        get() = servidorUrl.isNotBlank() && codigoEquipo.isNotBlank()
}
