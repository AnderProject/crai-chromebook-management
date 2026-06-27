package com.crai.chromebook.ui

import android.app.Activity
import android.app.admin.DevicePolicyManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.text.InputType
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import com.crai.chromebook.admin.CraiDeviceAdmin
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.service.OverlayService

/**
 * Diálogo de configuración del kiosko, protegido por el PIN del personal.
 * Se usa desde el login (modo manual) y desde la pantalla de espera (modo auto).
 */
object ConfigDialog {

    /** Pide el PIN y, si es correcto, abre el formulario de ajustes. */
    fun abrir(context: Context, prefs: Prefs, onGuardado: () -> Unit) {
        val input = EditText(context).apply {
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
            hint = "PIN del personal"
        }
        AlertDialog.Builder(context)
            .setTitle("Configuración (personal CRAI)")
            .setView(input)
            .setPositiveButton("Continuar") { _, _ ->
                if (input.text.toString() == prefs.pinStaff) ajustes(context, prefs, onGuardado)
                else toast(context, "PIN incorrecto")
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun ajustes(context: Context, prefs: Prefs, onGuardado: () -> Unit) {
        fun campo(hint: String, valor: String, numerico: Boolean = false, password: Boolean = false) =
            EditText(context).apply {
                this.hint = hint
                setText(valor)
                inputType = when {
                    password -> InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
                    numerico -> InputType.TYPE_CLASS_NUMBER
                    else -> InputType.TYPE_CLASS_TEXT
                }
            }

        val titUrl = etiqueta(context, "Servidor (deja vacío = modo manual)")
        val cUrl = campo("http://192.168.100.7:8000", prefs.servidorUrl)
        val titCod = etiqueta(context, "Código de esta Chromebook")
        val cCod = campo("CB-005", prefs.codigoEquipo)
        val titKey = etiqueta(context, "Clave del servidor (X-KIOSKO-KEY)")
        val cKey = campo("clave del servidor", prefs.apiKey)
        val titDur = etiqueta(context, "Duración manual (minutos)")
        val cDur = campo("60", prefs.duracionMinutos.toString(), numerico = true)
        val titPin = etiqueta(context, "Nuevo PIN (opcional)")
        val cPin = campo("PIN", "", password = true)

        val chkEstricto = CheckBox(context).apply {
            text = "Mantener pantalla fija (modo kiosko)"
            isChecked = prefs.kioskoEstricto
            setPadding(0, 24, 0, 0)
        }

        val btnSalir = Button(context).apply {
            text = "Salir del modo kiosko"
            setOnClickListener { /* se asigna abajo, cuando exista el diálogo */ }
        }

        val cont = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(56, 24, 56, 0)
            addView(titUrl); addView(cUrl)
            addView(titCod); addView(cCod)
            addView(titKey); addView(cKey)
            addView(titDur); addView(cDur)
            addView(titPin); addView(cPin)
            addView(chkEstricto)
            addView(etiqueta(context, "Zona del personal"))
            addView(btnSalir)
        }

        val protegido = esAdminActivo(context)
        val dlg = AlertDialog.Builder(context)
            .setTitle("Ajustes del kiosko")
            .setView(cont)
            .setPositiveButton("Guardar") { _, _ ->
                prefs.servidorUrl = cUrl.text.toString()
                prefs.codigoEquipo = cCod.text.toString()
                cKey.text.toString().trim().takeIf { it.isNotEmpty() }?.let { prefs.apiKey = it }
                cDur.text.toString().toIntOrNull()?.let { if (it in 1..600) prefs.duracionMinutos = it }
                val nuevoPin = cPin.text.toString().trim()
                if (nuevoPin.length >= 4) prefs.pinStaff = nuevoPin
                prefs.kioskoEstricto = chkEstricto.isChecked
                if (!chkEstricto.isChecked) (context as? Activity)?.liberarPantalla()
                toast(context, "Ajustes guardados")
                onGuardado()
            }
            .setNeutralButton(if (protegido) "✔ Protegido" else "Proteger equipo") { _, _ ->
                if (protegido) toast(context, "El equipo ya está protegido contra desinstalación")
                else activarProteccion(context)
            }
            .setNegativeButton("Cancelar", null)
            .show()

        // El botón "Salir del modo kiosko" cierra este diálogo y pide confirmación.
        btnSalir.setOnClickListener {
            dlg.dismiss()
            confirmarSalida(context)
        }
    }

    /** Confirma y, si aceptan, libera el equipo del modo kiosko para poder gestionarlo. */
    private fun confirmarSalida(context: Context) {
        AlertDialog.Builder(context)
            .setTitle("Salir del modo kiosko")
            .setMessage(
                "El equipo dejará de estar controlado: se suelta la pantalla fijada, " +
                    "se quita la protección y se abre la pantalla de la app para que puedas " +
                    "desinstalarla o gestionarla. ¿Continuar?"
            )
            .setPositiveButton("Sí, salir") { _, _ -> salirModoKiosko(context) }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun salirModoKiosko(context: Context) {
        // 1) Detener la burbuja flotante.
        try { context.stopService(Intent(context, OverlayService::class.java)) } catch (_: Exception) {}

        // 2) Soltar el screen pinning.
        (context as? Activity)?.liberarPantalla()

        // 3) Quitar el administrador de dispositivo (si está activo) para permitir desinstalar.
        try {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
            val comp = CraiDeviceAdmin.componente(context)
            if (dpm.isAdminActive(comp)) {
                @Suppress("DEPRECATION")
                dpm.removeActiveAdmin(comp)
            }
        } catch (_: Exception) {}

        // 4) Abrir la pantalla de detalles de la app (desde ahí se desinstala).
        try {
            context.startActivity(
                Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:${context.packageName}")
                ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        } catch (_: Exception) {
            toast(context, "Abre Ajustes → Aplicaciones para desinstalar")
        }

        // 5) Cerrar la app del kiosko para no quedar encima.
        (context as? Activity)?.finishAffinity()
    }

    /** True si la app ya es administrador de dispositivo activo. */
    private fun esAdminActivo(context: Context): Boolean {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        return dpm.isAdminActive(CraiDeviceAdmin.componente(context))
    }

    /** Lanza el flujo del sistema para activar la protección anti-desinstalación. */
    private fun activarProteccion(context: Context) {
        try {
            val intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
                putExtra(
                    DevicePolicyManager.EXTRA_DEVICE_ADMIN,
                    CraiDeviceAdmin.componente(context)
                )
                putExtra(
                    DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                    "Impide que el estudiante desinstale el kiosko del CRAI. " +
                        "El personal puede quitarlo desde Ajustes cuando lo necesite."
                )
            }
            (context as? Activity)?.startActivity(intent)
        } catch (e: Exception) {
            toast(context, "Este equipo no permite activar la protección")
        }
    }

    private fun etiqueta(context: Context, texto: String) = TextView(context).apply {
        text = texto
        setPadding(0, 24, 0, 0)
        textSize = 12f
    }

    private fun toast(context: Context, msg: String) =
        android.widget.Toast.makeText(context, msg, android.widget.Toast.LENGTH_SHORT).show()
}
