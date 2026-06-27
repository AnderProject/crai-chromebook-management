package com.crai.chromebook.ui

import android.animation.ObjectAnimator
import android.content.Intent
import android.content.res.ColorStateList
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.view.View
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.crai.chromebook.R
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
    private val intervaloMs = 2500L

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
        pedirPermisoOverlay()
        animarPulso()

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                while (true) {
                    sondear()
                    delay(intervaloMs)
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Pantalla de espera fijada solo si el personal activó el modo estricto.
        if (prefs.kioskoEstricto) fijarPantalla() else liberarPantalla()
    }

    /**
     * La burbuja de tiempo necesita el permiso "dibujar sobre otras apps". En la
     * Chromebook se concede una sola vez; si falta, abrimos los ajustes para que
     * el personal lo active.
     */
    private fun pedirPermisoOverlay() {
        if (!Settings.canDrawOverlays(this)) {
            try {
                startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                )
            } catch (_: Exception) {
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
                irSesion(p)
                return
            }
            // Equipo en mantenimiento → pantalla dedicada.
            if (r.estado_equipo == "mantenimiento") {
                startActivity(Intent(this, MantenimientoActivity::class.java))
                finish()
                return
            }
            // Equipo libre.
            b.txtEstado.text = traducirEstado(r.estado_equipo)
            pintarDot(r.estado_equipo)
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

    /** Pinta el punto de estado: verde disponible, ámbar reservado, rojo ocupado. */
    private fun pintarDot(estado: String?) {
        val color = when (estado) {
            "reservado" -> R.color.ambar
            "prestado", "mantenimiento" -> R.color.rojo
            else -> R.color.verde
        }
        b.dot.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(this, color))
    }

    /** Pulso animado detrás del icono (sensación de "en línea / disponible"). */
    private fun animarPulso() {
        val v: View = b.pulse
        listOf(
            ObjectAnimator.ofFloat(v, View.SCALE_X, 1f, 1.7f),
            ObjectAnimator.ofFloat(v, View.SCALE_Y, 1f, 1.7f),
            ObjectAnimator.ofFloat(v, View.ALPHA, 0.5f, 0f)
        ).forEach {
            it.duration = 1700
            it.repeatCount = ObjectAnimator.INFINITE
            it.repeatMode = ObjectAnimator.RESTART
            it.start()
        }
    }

    private fun irSesion(p: com.crai.chromebook.api.PrestamoDto) {
        val i = Intent(this, SesionActivity::class.java).apply {
            putExtra(SesionActivity.EXTRA_SERVIDOR, true)
            putExtra(SesionActivity.EXTRA_PRESTAMO_ID, p.id)
            putExtra(SesionActivity.EXTRA_NOMBRE, p.estudiante)
            putExtra(SesionActivity.EXTRA_CEDULA, p.cedula)
            putExtra(SesionActivity.EXTRA_FIN_MS, p.fin_ms)
            putExtra(SesionActivity.EXTRA_FOTO, p.foto_url)
        }
        startActivity(i)
        finish()
    }

    private fun hora(): String =
        SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
}
