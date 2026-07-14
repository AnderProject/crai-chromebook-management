package com.crai.chromebook

import android.app.Application
import android.content.ContentValues
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.util.Date

/**
 * Application con capturador global de errores no controlados. Si la app se
 * cierra por un crash, deja el detalle en un archivo de texto accesible desde
 * la app "Archivos" de la Chromebook, para poder diagnosticarlo sin ADB:
 *
 *   Android/data/com.crai.chromebook/files/crash.txt
 *
 * También intenta un Toast con el motivo. Luego deja que el sistema termine el
 * proceso normalmente (re-lanza al handler previo).
 */
class CraiApp : Application() {

    override fun onCreate() {
        super.onCreate()
        val previo = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { hilo, error ->
            try {
                val sw = StringWriter()
                error.printStackTrace(PrintWriter(sw))
                val texto = "CRAI Kiosko · crash\n${Date()}\n\n$sw"
                guardarCrash(texto)
                try {
                    Toast.makeText(this, "Error: ${error.javaClass.simpleName}: ${error.message}", Toast.LENGTH_LONG).show()
                } catch (_: Exception) {
                }
            } catch (_: Exception) {
            }
            previo?.uncaughtException(hilo, error)
        }
    }

    /** Guarda el crash en la carpeta Descargas (accesible desde la app Archivos). */
    private fun guardarCrash(texto: String) {
        // 1) Descargas vía MediaStore (Android 10+): visible en Archivos → Descargas.
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val cv = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, "CRAI_crash.txt")
                    put(MediaStore.Downloads.MIME_TYPE, "text/plain")
                }
                val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv)
                uri?.let { contentResolver.openOutputStream(it)?.use { os -> os.write(texto.toByteArray()) } }
            } else {
                @Suppress("DEPRECATION")
                val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                File(dir, "CRAI_crash.txt").writeText(texto)
            }
        } catch (_: Exception) {
        }
        // 2) Respaldo en la carpeta propia de la app (por si Descargas falla).
        try {
            File(getExternalFilesDir(null), "crash.txt").writeText(texto)
        } catch (_: Exception) {
        }
    }
}
