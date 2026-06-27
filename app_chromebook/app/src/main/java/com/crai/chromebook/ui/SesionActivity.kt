package com.crai.chromebook.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import coil.load
import coil.transform.CircleCropTransformation
import com.crai.chromebook.R
import com.crai.chromebook.data.AppDatabase
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.data.Reserva
import com.crai.chromebook.data.ReservaRepository
import com.crai.chromebook.databinding.ActivitySesionBinding
import com.crai.chromebook.service.OverlayService
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Pantalla de sesión. Dos modos:
 *  - SERVIDOR (reservas de Django): muestra los datos del estudiante (con foto)
 *    durante unos segundos de "bienvenida" y luego se MINIMIZA para que el
 *    estudiante pueda usar la Chromebook. El conteo del tiempo, el polling al
 *    servidor (devolución/extensión/bloqueo remoto) y la apertura del bloqueo
 *    los maneja `OverlayService` (sigue vivo aunque la app esté en segundo
 *    plano), que además dibuja la burbuja flotante con el tiempo restante.
 *  - LOCAL (login manual de respaldo): sesión a pantalla completa con cuenta
 *    regresiva propia; al llegar a 0 → bloqueo.
 */
class SesionActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVIDOR = "modo_servidor"
        const val EXTRA_PRESTAMO_ID = "prestamo_id"
        const val EXTRA_NOMBRE = "nombre"
        const val EXTRA_CEDULA = "cedula"
        const val EXTRA_FIN_MS = "fin_ms"
        const val EXTRA_FOTO = "foto_url"
        private const val SEGUNDOS_BIENVENIDA = 12
    }

    private lateinit var b: ActivitySesionBinding
    private val repo by lazy { ReservaRepository(AppDatabase.get(this).reservaDao()) }
    private val prefs by lazy { Prefs(this) }

    private val avisoMinutos = 5
    private var modoServidor = false

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
        val fotoUrl = intent.getStringExtra(EXTRA_FOTO)
        duracionTotalMs = (finMs - System.currentTimeMillis()).coerceAtLeast(1)

        b.txtNombre.text = nombre
        b.txtCedula.text = cedula
        b.btnDevolver.visibility = View.GONE // la devolución se hace en el sistema
        liberarPantalla() // durante la sesión NO se fija: el estudiante usa el equipo
        cargarFoto(fotoUrl)

        // El servicio toma el control del conteo/bloqueo/polling y la burbuja.
        iniciarServicioOverlay()

        // Bienvenida: muestra los datos ~12s y luego minimiza para liberar el equipo.
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                var segundos = 0
                while (true) {
                    val restante = (finMs - System.currentTimeMillis()).coerceAtLeast(0)
                    pintar(restante)
                    if (restante <= 0L) break // el servicio abrirá el bloqueo
                    if (segundos >= SEGUNDOS_BIENVENIDA) { moveTaskToBack(true); break }
                    segundos++
                    delay(1000L)
                }
            }
        }
    }

    private fun iniciarServicioOverlay() {
        val i = Intent(this, OverlayService::class.java).apply {
            putExtra(OverlayService.EXTRA_FIN_MS, finMs)
            putExtra(OverlayService.EXTRA_PRESTAMO_ID, prestamoId)
            putExtra(OverlayService.EXTRA_SERVIDOR, true)
        }
        ContextCompat.startForegroundService(this, i)
    }

    private fun cargarFoto(url: String?) {
        if (!url.isNullOrBlank()) {
            b.imgFoto.load(url) {
                crossfade(true)
                placeholder(R.drawable.ic_avatar)
                error(R.drawable.ic_avatar)
                transformations(CircleCropTransformation())
            }
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
                        irBloqueoLocal()
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

    private fun irBloqueoLocal() {
        startActivity(Intent(this, LockActivity::class.java)
            .putExtra(LockActivity.EXTRA_SERVIDOR, false))
        finish()
    }

    private fun irLogin() {
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
