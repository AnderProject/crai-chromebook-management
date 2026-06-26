package com.crai.chromebook.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.crai.chromebook.R
import com.crai.chromebook.api.ApiClient
import com.crai.chromebook.data.AppDatabase
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.data.Reserva
import com.crai.chromebook.data.ReservaRepository
import com.crai.chromebook.databinding.ActivitySesionBinding
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Sesión activa con cuenta regresiva. Funciona en dos modos:
 *  - LOCAL: la reserva vive en Room (login manual).
 *  - SERVIDOR: los datos vienen de un préstamo de Django; re-consulta el
 *    servidor para detectar devolución anticipada o extensión del tiempo.
 * Al llegar a 0 → pantalla de bloqueo.
 */
class SesionActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVIDOR = "modo_servidor"
        const val EXTRA_PRESTAMO_ID = "prestamo_id"
        const val EXTRA_NOMBRE = "nombre"
        const val EXTRA_CEDULA = "cedula"
        const val EXTRA_FIN_MS = "fin_ms"
    }

    private lateinit var b: ActivitySesionBinding
    private val repo by lazy { ReservaRepository(AppDatabase.get(this).reservaDao()) }
    private val prefs by lazy { Prefs(this) }

    private val avisoMinutos = 5
    private var modoServidor = false

    // Estado de la sesión actual (sirve para ambos modos).
    private var finMs = 0L
    private var duracionTotalMs = 0L
    private var prestamoId = 0L
    private var reservaLocal: Reserva? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivitySesionBinding.inflate(layoutInflater)
        setContentView(b.root)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { /* bloqueado */ }
        })

        modoServidor = intent.getBooleanExtra(EXTRA_SERVIDOR, false)

        if (modoServidor) iniciarServidor() else iniciarLocal()
    }

    // ---------------- MODO SERVIDOR ----------------

    private fun iniciarServidor() {
        prestamoId = intent.getLongExtra(EXTRA_PRESTAMO_ID, 0)
        finMs = intent.getLongExtra(EXTRA_FIN_MS, 0)
        val nombre = intent.getStringExtra(EXTRA_NOMBRE).orEmpty()
        val cedula = intent.getStringExtra(EXTRA_CEDULA).orEmpty()
        duracionTotalMs = (finMs - System.currentTimeMillis()).coerceAtLeast(1)

        b.txtNombre.text = nombre
        b.txtCedula.text = cedula
        b.btnDevolver.visibility = android.view.View.GONE // la devolución se hace en el sistema

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                var tick = 0
                while (true) {
                    val restante = (finMs - System.currentTimeMillis()).coerceAtLeast(0)
                    pintar(restante)
                    if (restante <= 0L) { irBloqueo(); break }
                    // Cada ~12s vuelve a consultar el servidor.
                    if (tick % 12 == 0) verificarServidor()
                    tick++
                    delay(1000L)
                }
            }
        }
    }

    /** Detecta devolución anticipada (vuelve a Espera) o extensión del tiempo. */
    private suspend fun verificarServidor() {
        try {
            val api = ApiClient.crear(prefs.servidorUrl)
            val r = api.estado(prefs.codigoEquipo, prefs.apiKey)
            val p = r.prestamo
            if (p == null || p.estado != "activo" || p.id != prestamoId) {
                irEspera() // el préstamo se cerró/devolvió en el sistema
            } else if (p.fin_ms != finMs) {
                finMs = p.fin_ms // tiempo extendido/ajustado desde el sistema
            }
        } catch (_: Exception) {
            // Sin conexión: seguimos con el tiempo ya conocido (modo tolerante).
        }
    }

    // ---------------- MODO LOCAL ----------------

    private fun iniciarLocal() {
        lifecycleScope.launch {
            val r = repo.activa()
            if (r == null) { irLogin(); return@launch }
            reservaLocal = r
            finMs = r.finPrevisto
            duracionTotalMs = r.duracionMinutos * 60_000L
            b.txtNombre.text = r.nombre
            b.txtCedula.text = r.cedula
            b.btnDevolver.setOnClickListener { confirmarDevolucion() }

            repeatOnLifecycle(Lifecycle.State.STARTED) {
                while (true) {
                    val restante = (finMs - System.currentTimeMillis()).coerceAtLeast(0)
                    pintar(restante)
                    if (restante <= 0L) {
                        repo.vencer(r)
                        irBloqueo()
                        break
                    }
                    delay(1000L)
                }
            }
        }
    }

    private fun confirmarDevolucion() {
        AlertDialog.Builder(this)
            .setTitle("Devolver Chromebook")
            .setMessage("¿Confirmas que terminaste tu sesión?")
            .setPositiveButton("Sí, devolver") { _, _ ->
                lifecycleScope.launch {
                    reservaLocal?.let { repo.devolver(it) }
                    irLogin()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    // ---------------- UI COMÚN ----------------

    private fun pintar(restanteMillis: Long) {
        b.txtContador.text = formato(restanteMillis)
        val progreso = if (duracionTotalMs > 0) (restanteMillis * 100 / duracionTotalMs).toInt() else 0
        b.barra.progress = progreso.coerceIn(0, 100)

        val enAviso = restanteMillis <= avisoMinutos * 60_000L
        val color = ContextCompat.getColor(this, if (enAviso) R.color.ambar else R.color.azul)
        b.root.setBackgroundColor(color)
    }

    private fun formato(millis: Long): String {
        val h = TimeUnit.MILLISECONDS.toHours(millis)
        val m = TimeUnit.MILLISECONDS.toMinutes(millis) % 60
        val s = TimeUnit.MILLISECONDS.toSeconds(millis) % 60
        return String.format("%02d:%02d:%02d", h, m, s)
    }

    private fun irBloqueo() {
        startActivity(Intent(this, LockActivity::class.java)
            .putExtra(LockActivity.EXTRA_SERVIDOR, modoServidor))
        finish()
    }

    private fun irEspera() {
        startActivity(Intent(this, EsperaActivity::class.java))
        finish()
    }

    private fun irLogin() {
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
