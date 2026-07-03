package com.crai.chromebook.data

import android.content.Context
import com.crai.chromebook.BuildConfig

/**
 * Configuración local del kiosko (editable por el personal del CRAI).
 *
 * Los valores de servidor/código/clave vienen PRE-CABLEADOS desde BuildConfig
 * (ver build.gradle.kts), así la app arranca ya en modo automático sin que
 * nadie teclee nada en la Chromebook. El personal puede sobreescribirlos desde
 * ⚙ (protegido por PIN); si los borra, vuelve a tomar el pre-cableado.
 *
 * OJO (placeholders de tesis): el PIN por defecto es "2468". Cámbialo en
 * producción desde la pantalla de configuración (botón ⚙ en el login).
 */
class Prefs(context: Context) {

    private val sp = context.getSharedPreferences("crai_kiosko", Context.MODE_PRIVATE)

    /**
     * Duración de la sesión manual (login de respaldo), en minutos.
     * 0 = SIN LÍMITE (la sesión no vence por tiempo; "para siempre").
     * En modo servidor el tiempo lo define la reserva de Django, no este valor.
     */
    var duracionMinutos: Int
        get() = sp.getInt("duracion", 0)
        set(v) = sp.edit().putInt("duracion", v.coerceAtLeast(0)).apply()

    var pinStaff: String
        get() = sp.getString("pin", "2468") ?: "2468"
        set(v) = sp.edit().putString("pin", v).apply()

    /**
     * Modo kiosko estricto: si está activo, las pantallas de espera, bloqueo y
     * mantenimiento "fijan" la pantalla (screen pinning) para que el estudiante
     * no pueda salir. Apágalo para usar la Chromebook con libertad en pruebas.
     */
    var kioskoEstricto: Boolean
        get() = sp.getBoolean("kiosko_estricto", false)
        set(v) = sp.edit().putBoolean("kiosko_estricto", v).apply()

    // ---- Modo servidor (Fase 4: autoconfiguración desde Django) ----

    /** URL base del servidor Django, ej. http://192.168.100.7:8000/ */
    var servidorUrl: String
        get() = sp.getString("servidor_url", BuildConfig.DEFAULT_SERVER_URL)
            ?: BuildConfig.DEFAULT_SERVER_URL
        set(v) = sp.edit().putString("servidor_url", v.trim()).apply()

    /** Código de inventario de ESTA Chromebook, ej. CB-005. */
    var codigoEquipo: String
        get() = sp.getString("codigo_equipo", BuildConfig.DEFAULT_CODIGO)
            ?: BuildConfig.DEFAULT_CODIGO
        set(v) = sp.edit().putString("codigo_equipo", v.trim()).apply()

    /** Clave compartida que se envía en el header X-KIOSKO-KEY. */
    var apiKey: String
        get() = sp.getString("api_key", BuildConfig.DEFAULT_API_KEY)
            ?: BuildConfig.DEFAULT_API_KEY
        set(v) = sp.edit().putString("api_key", v.trim()).apply()

    /** Hay modo automático si el equipo tiene servidor + código configurados. */
    val modoAuto: Boolean
        get() = servidorUrl.isNotBlank() && codigoEquipo.isNotBlank()
}
