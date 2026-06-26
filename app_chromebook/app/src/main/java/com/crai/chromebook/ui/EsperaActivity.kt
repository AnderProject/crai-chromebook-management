package com.crai.chromebook.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.crai.chromebook.api.ApiClient
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.databinding.ActivityEsperaBinding
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Pantalla de espera del modo automático: muestra el equipo "Disponible" y
 * consulta al servidor (polling) si hay un préstamo activo para esta Chromebook.
 * Cuando aparece uno, arranca la sesión automáticamente con los datos del
 * estudiante (sin escritura manual).
 */
class EsperaActivity : AppCompatActivity() {

    private lateinit var b: ActivityEsperaBinding
    private val prefs by lazy { Prefs(this) }
    private val intervaloMs = 8000L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityEsperaBinding.inflate(layoutInflater)
        setContentView(b.root)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { /* bloqueado */ }
        })

        b.btnConfig.setOnClickListener {
            ConfigDialog.abrir(this, prefs) { recargar() }
        }

        recargar()

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                while (true) {
                    sondear()
                    delay(intervaloMs)
                }
            }
        }
    }

    private fun recargar() {
        b.txtCodigo.text = prefs.codigoEquipo.ifBlank { "Sin código" }
        // Si quitaron la config del servidor, volver al login manual.
        if (!prefs.modoAuto) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    private suspend fun sondear() {
        try {
            val api = ApiClient.crear(prefs.servidorUrl)
            val r = api.estado(prefs.codigoEquipo, prefs.apiKey)
            val p = r.prestamo
            if (p != null && p.estado == "activo" && p.fin_ms > System.currentTimeMillis()) {
                irSesion(p.id, p.estudiante, p.cedula, p.fin_ms)
                return
            }
            // Equipo libre.
            b.txtEstado.text = traducirEstado(r.estado_equipo)
            b.txtSub.text = "Esperando una reserva desde el sistema…"
            b.txtConexion.text = "Conectado · ${hora()}"
        } catch (e: Exception) {
            b.txtConexion.text = "Sin conexión con el servidor · reintentando…"
        }
    }

    private fun traducirEstado(estado: String?): String = when (estado) {
        "disponible" -> "Disponible"
        "reservado" -> "Reservado"
        "mantenimiento" -> "En mantenimiento"
        "prestado" -> "Prestado"
        else -> "Disponible"
    }

    private fun irSesion(id: Long, nombre: String, cedula: String, finMs: Long) {
        val i = Intent(this, SesionActivity::class.java).apply {
            putExtra(SesionActivity.EXTRA_SERVIDOR, true)
            putExtra(SesionActivity.EXTRA_PRESTAMO_ID, id)
            putExtra(SesionActivity.EXTRA_NOMBRE, nombre)
            putExtra(SesionActivity.EXTRA_CEDULA, cedula)
            putExtra(SesionActivity.EXTRA_FIN_MS, finMs)
        }
        startActivity(i)
        finish()
    }

    private fun hora(): String =
        SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
}
