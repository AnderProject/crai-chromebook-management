package com.crai.chromebook.ui

import android.content.Intent
import android.os.Bundle
import android.text.InputType
import android.view.WindowManager
import android.widget.EditText
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.crai.chromebook.api.ApiClient
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.databinding.ActivityLockBinding
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Pantalla de bloqueo a tiempo vencido. Solo el personal del CRAI puede salir
 * con el PIN. En modo servidor, además consulta a Django: si el préstamo se
 * cierra/devuelve en el sistema, la Chromebook se desbloquea sola y vuelve a
 * Espera.
 */
class LockActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVIDOR = "modo_servidor"
    }

    private lateinit var b: ActivityLockBinding
    private val prefs by lazy { Prefs(this) }
    private var modoServidor = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityLockBinding.inflate(layoutInflater)
        setContentView(b.root)
        entrarPantallaCompleta()

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        modoServidor = intent.getBooleanExtra(EXTRA_SERVIDOR, false)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { /* bloqueado */ }
        })

        animarPop(b.lockIcono)
        animarEntrada(b.lockTitulo, b.txtLockMsg)

        b.btnDesbloquear.setOnClickListener { pedirPin() }

        // Al bloquear, la burbuja de tiempo ya no aplica.
        stopService(Intent(this, com.crai.chromebook.service.OverlayService::class.java))

        if (modoServidor) {
            lifecycleScope.launch {
                repeatOnLifecycle(Lifecycle.State.STARTED) {
                    while (true) {
                        if (debeDesbloquear()) { irEspera(); break }
                        delay(2500L)
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        entrarPantallaCompleta()
        // En modo estricto el bloqueo fija la pantalla para que no puedan escapar.
        if (prefs.kioskoEstricto) fijarPantalla()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) entrarPantallaCompleta()
    }

    /**
     * Decide, según el servidor, si la Chromebook debe SALIR del bloqueo:
     *  - préstamo devuelto/cerrado → vuelve a Espera (Disponible);
     *  - préstamo activo, SIN bloqueo remoto y con tiempo vigente → reanuda la
     *    sesión (cubre el desbloqueo desde el dashboard y la extensión de tiempo).
     * Si el bloqueo es por tiempo vencido (sin tiempo) o sigue bloqueado en el
     * sistema, permanece bloqueada.
     */
    private suspend fun debeDesbloquear(): Boolean = try {
        val r = ApiClient.crear(prefs.servidorUrl).estado(prefs.codigoEquipo, prefs.apiKey)
        val p = r.prestamo
        when {
            p == null || p.estado != "activo" -> true
            else -> !p.bloqueado && p.fin_ms > System.currentTimeMillis()
        }
    } catch (_: Exception) {
        false
    }

    private fun pedirPin() {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
            hint = "PIN del personal"
        }
        AlertDialog.Builder(this)
            .setTitle("Desbloquear")
            .setMessage("Ingresa el PIN del personal del CRAI.")
            .setView(input)
            .setPositiveButton("Desbloquear") { _, _ ->
                if (input.text.toString() == prefs.pinStaff) salir()
                else AlertDialog.Builder(this)
                    .setMessage("PIN incorrecto.")
                    .setPositiveButton("OK", null)
                    .show()
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun salir() {
        liberarPantalla() // quita el screen pinning al desbloquear legítimamente
        if (modoServidor) {
            // Si el bloqueo vino del dashboard, limpiamos el flag para que no se
            // vuelva a bloquear; luego Espera reanuda la sesión si sigue vigente.
            lifecycleScope.launch {
                try {
                    ApiClient.crear(prefs.servidorUrl).desbloquear(prefs.codigoEquipo, prefs.apiKey)
                } catch (_: Exception) {
                }
                irEspera()
            }
        } else {
            val destino = if (prefs.modoAuto) EsperaActivity::class.java else LoginActivity::class.java
            irCon(destino)
        }
    }

    private fun irEspera() {
        irCon(EsperaActivity::class.java)
    }
}
