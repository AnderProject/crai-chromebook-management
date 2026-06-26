# Kiosko CRAI — App Chromebook (Android / Kotlin)

App de control de uso de Chromebooks tipo *cyber* para el CRAI. Registra el
inicio de la reserva del estudiante, lleva la cuenta regresiva del tiempo y, al
vencer, **bloquea** la pantalla hasta que el personal del CRAI la desbloquea con
un PIN.

> Forma parte del proyecto de tesis `proyecto_crai` (backend Django). Esta app
> vive en la subcarpeta `app_chromebook/`.

## Estado actual (Fase 1 + 2 ✅)

- [x] Proyecto Android scaffoldeado (Gradle + Kotlin + ViewBinding).
- [x] **Caché local con Room**: la reserva (cédula, nombre, inicio, duración,
      estado) se guarda en SQLite. El tiempo se calcula contra el reloj real, así
      que aunque se cierre/reinicie la app, al reabrir recupera el estado.
- [x] Flujo completo **offline**: Login → Sesión (contador) → Bloqueo.
- [x] Pantalla de bloqueo con desbloqueo por PIN del personal.
- [x] Configuración del kiosko (duración y PIN) protegida por PIN (botón ⚙).

### Pendiente (próximas fases)

- [ ] **Fase 3 — Screen pinning / Lock Task Mode**: fijar la app para que el
      estudiante no pueda minimizarla ni cambiar de app.
- [ ] **Fase 4 — Sync con Django**: enviar reservas al backend (Retrofit + las
      dependencias ya están incluidas), validar al estudiante online y reflejar
      el préstamo en el panel admin. Modo híbrido (cola offline con WorkManager).

## Cómo abrir y compilar

1. Instala **Android Studio** (trae JDK 17 + SDK + emulador + adb):
   https://developer.android.com/studio
2. Android Studio → **Open** → selecciona la carpeta `app_chromebook/`.
3. Espera el **Gradle Sync** (descarga dependencias la primera vez).
4. Ejecuta ▶ en un **emulador** (o en la Chromebook por adb / Play Store interno).

> Desde terminal también: `./gradlew assembleDebug` genera el APK en
> `app/build/outputs/apk/debug/app-debug.apk`.

## Instalar en la Chromebook

1. En la Chromebook: Configuración → activar **apps de Android** (Play Store).
2. Activar **Modo desarrollador** o usar `adb` por red para instalar el APK
   (sideload). Alternativa: subirlo como app interna si la institución administra
   los equipos.
3. (Fase 3) Activar **Fijar pantalla**: Configuración → Seguridad → Fijar pantalla.

## Valores por defecto (cambiar en producción)

| Ajuste | Valor por defecto | Dónde cambiarlo |
|--------|-------------------|-----------------|
| Duración de la reserva | 60 min | Botón ⚙ en el login |
| PIN del personal | `2468` | Botón ⚙ en el login |

## Limitación conocida (Chromebooks NO administradas)

Sin gestión de dispositivos (Google Admin), el bloqueo no es 100% inviolable: un
estudiante decidido podría salir del *screen pinning*. Es suficiente para control
de uso y trazabilidad. Para un bloqueo a prueba de todo se requiere inscribir las
Chromebooks en un dominio administrado (kiosko de ChromeOS).

## Estructura

```
app_chromebook/
├─ app/
│  ├─ build.gradle.kts
│  └─ src/main/
│     ├─ AndroidManifest.xml
│     ├─ java/com/crai/chromebook/
│     │  ├─ data/        # Room: Reserva, DAO, BD, Repository, Prefs
│     │  └─ ui/          # LoginActivity, SesionActivity, LockActivity
│     └─ res/            # layouts, colores (azul CRAI), strings, tema, icono
├─ build.gradle.kts      # plugins raíz
└─ settings.gradle.kts
```
