package com.crai.chromebook.ui

import android.content.Context
import android.text.InputType
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import com.crai.chromebook.data.Prefs

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

        val cont = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(56, 24, 56, 0)
            addView(titUrl); addView(cUrl)
            addView(titCod); addView(cCod)
            addView(titKey); addView(cKey)
            addView(titDur); addView(cDur)
            addView(titPin); addView(cPin)
        }

        AlertDialog.Builder(context)
            .setTitle("Ajustes del kiosko")
            .setView(cont)
            .setPositiveButton("Guardar") { _, _ ->
                prefs.servidorUrl = cUrl.text.toString()
                prefs.codigoEquipo = cCod.text.toString()
                cKey.text.toString().trim().takeIf { it.isNotEmpty() }?.let { prefs.apiKey = it }
                cDur.text.toString().toIntOrNull()?.let { if (it in 1..600) prefs.duracionMinutos = it }
                val nuevoPin = cPin.text.toString().trim()
                if (nuevoPin.length >= 4) prefs.pinStaff = nuevoPin
                toast(context, "Ajustes guardados")
                onGuardado()
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun etiqueta(context: Context, texto: String) = TextView(context).apply {
        text = texto
        setPadding(0, 24, 0, 0)
        textSize = 12f
    }

    private fun toast(context: Context, msg: String) =
        android.widget.Toast.makeText(context, msg, android.widget.Toast.LENGTH_SHORT).show()
}
