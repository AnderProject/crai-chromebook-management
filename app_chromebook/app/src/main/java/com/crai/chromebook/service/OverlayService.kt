package com.crai.chromebook.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.TextView
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.crai.chromebook.R
import com.crai.chromebook.api.ApiClient
import com.crai.chromebook.data.Prefs
import com.crai.chromebook.ui.EsperaActivity
import com.crai.chromebook.ui.LockActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit

/**
 * Burbuja flotante (estilo "cyber") + cerebro de la sesión en modo servidor.
 *
 * Dibuja una vista ENCIMA de cualquier app (Chrome incluido) con el tiempo
 * restante, usando el permiso "dibujar sobre otras apps". Como sigue vivo en
 * primer plano aunque la app esté minimizada, también es quien:
 *   - cuenta el tiempo y, al llegar a 0, abre la pantalla de bloqueo;
 *   - consulta al servidor (polling) para detectar devolución anticipada,
 *     extensión del tiempo o BLOQUEO REMOTO desde el dashboard.
 *
 * En modo local (login manual) solo muestra el tiempo; la propia SesiónActivity
 * maneja su bloqueo, así que el servicio no se usa ahí.
 */
class OverlayService : Service() {

    companion object {
        const val EXTRA_FIN_MS = "fin_ms"
        const val EXTRA_PRESTAMO_ID = "prestamo_id"
        const val EXTRA_SERVIDOR = "modo_servidor"
        const val ACTION_STOP = "com.crai.chromebook.OVERLAY_STOP"
        private const val CANAL_ID = "kiosko_overlay"
        private const val NOTIF_ID = 4711
        private const val AVISO_MIN = 5
    }

    private val prefs by lazy { Prefs(this) }
    private var wm: WindowManager? = null
    private var vista: View? = null
    private var txt: TextView? = null

    private var finMs = 0L
    private var prestamoId = 0L
    private var modoServidor = false
    private var terminando = false

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var tarea: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }

        finMs = intent?.getLongExtra(EXTRA_FIN_MS, 0L) ?: 0L
        prestamoId = intent?.getLongExtra(EXTRA_PRESTAMO_ID, 0L) ?: 0L
        modoServidor = intent?.getBooleanExtra(EXTRA_SERVIDOR, false) ?: false
        arrancarPrimerPlano()
        mostrarBurbuja()
        iniciarConteo()
        return START_STICKY
    }

    private fun arrancarPrimerPlano() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val canal = NotificationChannel(
                CANAL_ID,
                getString(R.string.overlay_canal),
                NotificationManager.IMPORTANCE_LOW
            ).apply { setShowBadge(false) }
            nm.createNotificationChannel(canal)
        }
        val notif = NotificationCompat.Builder(this, CANAL_ID)
            .setContentTitle("Sesión de Chromebook en curso")
            .setContentText("Tu tiempo de uso se está contando.")
            .setSmallIcon(R.drawable.ic_launcher)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIF_ID, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(NOTIF_ID, notif)
        }
    }

    private fun mostrarBurbuja() {
        if (vista != null) return
        wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val v = LayoutInflater.from(this).inflate(R.layout.overlay_tiempo, null)
        txt = v.findViewById(R.id.overlayTiempo)

        val tipo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else
            @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            tipo,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            x = dp(12)
            y = dp(12)
        }

        try {
            wm?.addView(v, lp)
            vista = v
        } catch (_: Exception) {
            // Sin permiso de overlay: la sesión sigue, solo no se ve la burbuja.
        }
    }

    private fun iniciarConteo() {
        tarea?.cancel()
        terminando = false
        tarea = scope.launch {
            var tick = 0
            while (true) {
                val restante = (finMs - System.currentTimeMillis()).coerceAtLeast(0)
                pintar(restante)
                if (restante <= 0L) { abrirBloqueo(); break }
                if (modoServidor && tick % 10 == 0) consultarServidor()
                if (terminando) break
                tick++
                delay(1000L)
            }
        }
    }

    /** Polling: devolución anticipada → Espera; bloqueo remoto → Bloqueo; extensión → ajusta. */
    private suspend fun consultarServidor() {
        try {
            val api = ApiClient.crear(prefs.servidorUrl)
            val r = api.estado(prefs.codigoEquipo, prefs.apiKey)
            val p = r.prestamo
            when {
                p == null || p.estado != "activo" || p.id != prestamoId -> abrirEspera()
                p.bloqueado -> abrirBloqueo()
                p.fin_ms != finMs -> finMs = p.fin_ms // tiempo extendido/ajustado
            }
        } catch (_: Exception) {
            // Sin conexión: seguimos con el tiempo conocido (modo tolerante).
        }
    }

    private fun abrirBloqueo() {
        if (terminando) return
        terminando = true
        lanzar(Intent(this, LockActivity::class.java)
            .putExtra(LockActivity.EXTRA_SERVIDOR, modoServidor))
    }

    private fun abrirEspera() {
        if (terminando) return
        terminando = true
        lanzar(Intent(this, EsperaActivity::class.java))
    }

    private fun lanzar(intent: Intent) {
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        try { startActivity(intent) } catch (_: Exception) {}
        stopSelf()
    }

    private fun pintar(restanteMillis: Long) {
        val t = txt ?: return
        t.text = formato(restanteMillis)
        val enAviso = restanteMillis <= AVISO_MIN * 60_000L
        t.setTextColor(ContextCompat.getColor(this, if (enAviso) R.color.ambar else R.color.blanco))
    }

    private fun formato(millis: Long): String {
        val h = TimeUnit.MILLISECONDS.toHours(millis)
        val m = TimeUnit.MILLISECONDS.toMinutes(millis) % 60
        val s = TimeUnit.MILLISECONDS.toSeconds(millis) % 60
        return String.format("%02d:%02d:%02d", h, m, s)
    }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    override fun onDestroy() {
        scope.cancel()
        vista?.let { try { wm?.removeView(it) } catch (_: Exception) {} }
        vista = null
        super.onDestroy()
    }
}
