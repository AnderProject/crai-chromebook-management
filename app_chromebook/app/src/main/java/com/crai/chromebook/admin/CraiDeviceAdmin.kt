package com.crai.chromebook.admin

import android.app.admin.DeviceAdminReceiver
import android.content.ComponentName
import android.content.Context

/**
 * Administrador de dispositivo del kiosko. Mientras está ACTIVO, el sistema no
 * deja desinstalar la app sin antes desactivarlo (lo hace el personal del CRAI
 * desde Ajustes). Es una capa de "estorbo" contra el estudiante; la verdad
 * última del préstamo siempre vive en Django.
 */
class CraiDeviceAdmin : DeviceAdminReceiver() {
    companion object {
        fun componente(context: Context) =
            ComponentName(context, CraiDeviceAdmin::class.java)
    }
}
