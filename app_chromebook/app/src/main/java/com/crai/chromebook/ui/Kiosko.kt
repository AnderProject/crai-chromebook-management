package com.crai.chromebook.ui

import android.app.Activity
import android.app.ActivityManager
import android.content.Context

/**
 * Utilidades de "modo kiosko" reutilizadas por las pantallas.
 *
 * Screen pinning (Lock Task) evita que el estudiante minimice la app o se vaya
 * a otra. En Chromebooks NO administradas el bloqueo es de "mejor esfuerzo":
 * el sistema puede pedir confirmación y el usuario muy hábil puede salir; la
 * verdad última sigue siendo el préstamo en Django. Por eso envolvemos todo en
 * try/catch: si el dispositivo no lo soporta, la app sigue funcionando igual.
 */

fun Activity.fijarPantalla() {
    try {
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
