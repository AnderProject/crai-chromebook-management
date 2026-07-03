package com.crai.chromebook.ui

import android.animation.ObjectAnimator
import android.app.Activity
import android.content.Intent
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.crai.chromebook.R

/**
 * Helpers visuales del kiosko: pantalla completa inmersiva, animaciones de
 * entrada/salida y transiciones entre pantallas (estética moderna/"cyber").
 * Se mantienen aquí para que todas las Activities compartan el mismo estilo.
 */

/**
 * Oculta las barras de estado y navegación (inmersivo pegajoso). El contenido
 * ocupa TODA la pantalla; si el usuario desliza desde el borde, las barras
 * aparecen un momento y se vuelven a ocultar. Llamar en onCreate, onResume y
 * onWindowFocusChanged para que se mantenga.
 */
fun Activity.entrarPantallaCompleta() {
    try {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val c = WindowInsetsControllerCompat(window, window.decorView)
        c.hide(WindowInsetsCompat.Type.systemBars())
        c.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
    } catch (_: Exception) {
    }
}

/**
 * Animación de entrada escalonada: cada vista sube y aparece con un pequeño
 * retraso respecto a la anterior (sensación fluida y profesional).
 */
fun animarEntrada(vararg vistas: View, desdeY: Float = 48f, retrasoBase: Long = 60L, paso: Long = 85L) {
    vistas.forEachIndexed { i, v ->
        v.alpha = 0f
        v.translationY = desdeY
        v.animate()
            .alpha(1f)
            .translationY(0f)
            .setStartDelay(retrasoBase + i * paso)
            .setDuration(520)
            .setInterpolator(DecelerateInterpolator())
            .start()
    }
}

/** Entrada tipo "pop" (escala con rebote suave), ideal para íconos/tarjetas. */
fun animarPop(vararg vistas: View, retrasoBase: Long = 40L, paso: Long = 90L) {
    vistas.forEachIndexed { i, v ->
        v.alpha = 0f
        v.scaleX = 0.7f
        v.scaleY = 0.7f
        v.animate()
            .alpha(1f)
            .scaleX(1f)
            .scaleY(1f)
            .setStartDelay(retrasoBase + i * paso)
            .setDuration(560)
            .setInterpolator(OvershootInterpolator(1.6f))
            .start()
    }
}

/** Pulso "radar" infinito: la vista crece y se desvanece en bucle. */
fun animarPulsoInfinito(v: View) {
    listOf(
        ObjectAnimator.ofFloat(v, View.SCALE_X, 1f, 1.7f),
        ObjectAnimator.ofFloat(v, View.SCALE_Y, 1f, 1.7f),
        ObjectAnimator.ofFloat(v, View.ALPHA, 0.5f, 0f)
    ).forEach {
        it.duration = 1700
        it.repeatCount = ObjectAnimator.INFINITE
        it.repeatMode = ObjectAnimator.RESTART
        it.start()
    }
}

/** Muestra una vista con fundido de entrada (para el overlay de desconexión). */
fun View.mostrarConFade(duracion: Long = 320L) {
    if (visibility == View.VISIBLE && alpha == 1f) return
    animate().cancel()
    alpha = 0f
    visibility = View.VISIBLE
    animate().alpha(1f).setDuration(duracion).setInterpolator(DecelerateInterpolator()).start()
}

/** Oculta una vista con fundido de salida. */
fun View.ocultarConFade(duracion: Long = 320L) {
    if (visibility != View.VISIBLE) return
    animate().cancel()
    animate().alpha(0f).setDuration(duracion).withEndAction {
        alpha = 1f
        visibility = View.GONE
    }.start()
}

/**
 * Navega a otra Activity con transición animada (fundido + deslizamiento).
 * `cerrar = true` cierra la actual (flujo de kiosko, sin volver atrás).
 */
fun Activity.irCon(destino: Class<*>, cerrar: Boolean = true, extras: (Intent.() -> Unit)? = null) {
    val i = Intent(this, destino)
    extras?.invoke(i)
    startActivity(i)
    @Suppress("DEPRECATION")
    overridePendingTransition(R.anim.kiosko_enter, R.anim.kiosko_exit)
    if (cerrar) finish()
}

/** Aplica la transición animada a un Intent ya construido. */
fun Activity.irCon(intent: Intent, cerrar: Boolean = true) {
    startActivity(intent)
    @Suppress("DEPRECATION")
    overridePendingTransition(R.anim.kiosko_enter, R.anim.kiosko_exit)
    if (cerrar) finish()
}
