package com.crai.chromebook.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.crai.chromebook.data.AppDatabase
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.data.ReservaRepository
import com.crai.chromebook.databinding.ActivityLoginBinding
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

/**
 * Pantalla inicial y "router":
 *  - Si hay una reserva LOCAL activa → sesión o bloqueo (modo manual).
 *  - Si está configurado el modo automático (servidor + código) → Espera.
 *  - Si no, muestra el login manual (respaldo para préstamos walk-in).
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var b: ActivityLoginBinding
    private val repo by lazy { ReservaRepository(AppDatabase.get(this).reservaDao()) }
    private val prefs by lazy { Prefs(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(b.root)
        entrarPantallaCompleta()

        b.btnIniciar.setOnClickListener { iniciar() }
        b.btnConfig.setOnClickListener {
            ConfigDialog.abrir(this, prefs) { enrutar() }
        }

        enrutar()
    }

    override fun onResume() {
        super.onResume()
        entrarPantallaCompleta()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) entrarPantallaCompleta()
    }

    /** Decide a qué pantalla ir según el estado local y la configuración. */
    private fun enrutar() {
        lifecycleScope.launch {
            val activa = repo.activa()
            if (activa != null) {
                if (activa.restanteMillis() > 0L) irA(SesionActivity::class.java)
                else { repo.vencer(activa); irA(LockActivity::class.java) }
                return@launch
            }
            if (prefs.modoAuto) irA(EsperaActivity::class.java)
        }
    }

    private fun iniciar() {
        val cedula = b.inputCedula.text?.toString()?.trim().orEmpty()
        val nombre = b.inputNombre.text?.toString()?.trim().orEmpty()

        if (cedula.length < 6) { aviso("Ingresa una cédula válida"); return }
        if (nombre.isEmpty()) { aviso("Ingresa tu nombre completo"); return }

        lifecycleScope.launch {
            repo.iniciar(cedula, nombre, prefs.duracionMinutos)
            irA(SesionActivity::class.java)
        }
    }

    private fun aviso(msg: String) =
        Snackbar.make(b.root, msg, Snackbar.LENGTH_SHORT).show()

    private fun irA(clazz: Class<*>) {
        irCon(clazz)
    }
}
