package com.crai.chromebook.ui

import android.app.Activity
import android.app.ActivityManager
import android.app.admin.DevicePolicyManager
import android.content.Context
import android.os.Build
import com.crai.chromebook.admin.CraiDeviceAdmin

/**
 * Utilidades de "modo kiosko" reutilizadas por las pantallas.
 *
 * Screen pinning (Lock Task) evita que el estudiante minimice la app o se vaya
 * a otra.
 *
 * Hay DOS niveles según cómo esté aprovisionada la Chromebook:
 *  - **Device Owner** (recomendado): si la app se registró como propietario del
 *    dispositivo (una sola vez por ADB, ver README), el Lock Task es SILENCIOSO:
 *    entra directo a pantalla completa, sin la ventanita de confirmación ni el
 *    aviso de "mantén pulsado para salir". El estudiante no puede escapar.
 *  - **Mejor esfuerzo** (sin Device Owner): `startLockTask()` usa el screen
 *    pinning normal de Android, que muestra confirmación/aviso y un usuario muy
 *    hábil podría salir. La verdad última sigue siendo el préstamo en Django.
 *
 * Todo va envuelto en try/catch: si el dispositivo no lo soporta, la app sigue.
 *
 * Para activar el modo silencioso, una sola vez y con la Chromebook sin cuentas:
 *   adb shell dpm set-device-owner com.crai.chromebook/.admin.CraiDeviceAdmin
 */

fun Activity.fijarPantalla() {
    try {
        prepararLockTaskSilencioso()
        val am = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        @Suppress("DEPRECATION")
        val enLockTask = am.lockTaskModeState != ActivityManager.LOCK_TASK_MODE_NONE
        if (!enLockTask) startLockTask()
    } catch (_: Exception) {
        // El dispositivo no permite Lock Task (ej. ChromeOS sin política): se ignora.
    }
}

fun Activity.liberarPantalla() {
    try {
        stopLockTask()
    } catch (_: Exception) {
    }
}

/** True si la app es propietaria del dispositivo (pinning silencioso disponible). */
fun Activity.esDeviceOwner(): Boolean = try {
    val dpm = getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    dpm.isDeviceOwnerApp(packageName)
} catch (_: Exception) {
    false
}

/**
 * Si somos Device Owner, autoriza a ESTA app en el Lock Task para que el pinning
 * sea silencioso (sin diálogo ni aviso del sistema) y deja visibles solo los
 * elementos imprescindibles del sistema.
 */
private fun Activity.prepararLockTaskSilencioso() {
    try {
        val dpm = getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        if (!dpm.isDeviceOwnerApp(packageName)) return
        val admin = CraiDeviceAdmin.componente(this)
        dpm.setLockTaskPackages(admin, arrayOf(packageName))
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            // Sin barra de notificaciones ni Home/Recientes: kiosko real.
            dpm.setLockTaskFeatures(
                admin,
                DevicePolicyManager.LOCK_TASK_FEATURE_GLOBAL_ACTIONS or
                    DevicePolicyManager.LOCK_TASK_FEATURE_KEYGUARD
            )
        }
    } catch (_: Exception) {
    }
}
