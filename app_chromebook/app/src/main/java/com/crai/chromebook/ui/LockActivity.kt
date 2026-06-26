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

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        modoServidor = intent.getBooleanExtra(EXTRA_SERVIDOR, false)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { /* bloqueado */ }
        })

        b.btnDesbloquear.setOnClickListener { pedirPin() }

        if (modoServidor) {
            lifecycleScope.launch {
                repeatOnLifecycle(Lifecycle.State.STARTED) {
                    while (true) {
                        if (prestamoCerrado()) { irEspera(); break }
                        delay(10000L)
                    }
                }
            }
        }
    }

    /** True si el servidor ya no reporta un préstamo activo para este equipo. */
    private suspend fun prestamoCerrado(): Boolean = try {
        val api = ApiClient.crear(prefs.servidorUrl)
        val r = api.estado(prefs.codigoEquipo, prefs.apiKey)
        val p = r.prestamo
        p == null || p.estado != "activo"
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
        val destino = if (modoServidor || prefs.modoAuto) EsperaActivity::class.java else LoginActivity::class.java
        startActivity(Intent(this, destino))
        finish()
    }

    private fun irEspera() {
        startActivity(Intent(this, EsperaActivity::class.java))
        finish()
    }
}
