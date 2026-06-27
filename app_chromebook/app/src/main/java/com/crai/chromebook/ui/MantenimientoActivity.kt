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
import com.crai.chromebook.databinding.ActivityMantenimientoBinding
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Pantalla mostrada cuando el servidor reporta que esta Chromebook está en
 * estado "mantenimiento". El estudiante no puede usarla. Consulta al servidor
 * y, en cuanto el equipo vuelve a estar disponible (el personal lo saca de
 * mantenimiento en el sistema), regresa sola a la pantalla de Espera.
 */
class MantenimientoActivity : AppCompatActivity() {

    private lateinit var b: ActivityMantenimientoBinding
    private val prefs by lazy { Prefs(this) }
    private val intervaloMs = 8000L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMantenimientoBinding.inflate(layoutInflater)
        setContentView(b.root)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { /* bloqueado */ }
        })

        b.txtCodigo.text = prefs.codigoEquipo.ifBlank { "Sin código" }
        b.btnConfig.setOnClickListener {
            ConfigDialog.abrir(this, prefs) { /* al guardar, el polling decidirá */ }
        }

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
        if (prefs.kioskoEstricto) fijarPantalla() else liberarPantalla()
    }

    private suspend fun sondear() {
        try {
            val api = ApiClient.crear(prefs.servidorUrl)
            val r = api.estado(prefs.codigoEquipo, prefs.apiKey)
            // Si ya no está en mantenimiento, volvemos a la pantalla de Espera.
            if (r.estado_equipo != "mantenimiento") {
                startActivity(Intent(this, EsperaActivity::class.java))
                finish()
                return
            }
            b.txtConexion.text = "Conectado · ${hora()}"
        } catch (e: Exception) {
            b.txtConexion.text = "Sin conexión con el servidor · reintentando…"
        }
    }

    private fun hora(): String =
        SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
}
