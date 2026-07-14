"""Establece la foto de perfil del bot de WhatsApp (perfil de empresa del número).

La foto NO se manda por mensaje: es la imagen del PERFIL del número de WhatsApp
Business. Se sube UNA vez con la API de Meta y queda para todos los chats.

Flujo (API de Meta):
  1) Se inicia una sesión de subida reanudable en /{APP_ID}/uploads.
  2) Se sube el binario de la imagen y se obtiene un "handle".
  3) Se asigna ese handle como profile_picture_handle en
     /{PHONE_NUMBER_ID}/whatsapp_business_profile.

Requisitos en .env:
  WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_APP_ID

Uso:
  python manage.py set_whatsapp_foto --imagen ruta/al/logo.png
  (Imagen cuadrada JPG/PNG; Meta recomienda mínimo 640x640.)
"""
import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Sube una imagen y la fija como foto de perfil del número de WhatsApp Business.'

    def add_arguments(self, parser):
        parser.add_argument('--imagen', required=True,
                            help='Ruta a la imagen (JPG o PNG, cuadrada, ideal 640x640).')

    def _fail(self, msg):
        self.stderr.write(self.style.ERROR(msg))

    def handle(self, *args, **opts):
        token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '') or ''
        pnid = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '') or ''
        app_id = getattr(settings, 'WHATSAPP_APP_ID', '') or ''
        ver = getattr(settings, 'WHATSAPP_API_VERSION', 'v21.0') or 'v21.0'
        ruta = opts['imagen']

        if not token or not pnid:
            return self._fail('Falta WHATSAPP_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID en el .env.')
        if not app_id:
            return self._fail('Falta WHATSAPP_APP_ID en el .env (el ID de tu app de Meta, en '
                              'developers.facebook.com → tu app → Configuración).')
        if not os.path.exists(ruta):
            return self._fail(f'No se encontró la imagen: {ruta}')

        data = open(ruta, 'rb').read()
        ctype = 'image/png' if ruta.lower().endswith('.png') else 'image/jpeg'
        base = f'https://graph.facebook.com/{ver}'

        # 1) Iniciar sesión de subida reanudable.
        self.stdout.write('1/3 Iniciando la subida…')
        r = requests.post(f'{base}/{app_id}/uploads',
                          params={'file_length': len(data), 'file_type': ctype, 'access_token': token},
                          timeout=30)
        if r.status_code >= 400:
            return self._fail(f'Error al iniciar la subida: {r.text[:400]}')
        session_id = r.json().get('id')
        if not session_id:
            return self._fail(f'No se obtuvo la sesión de subida: {r.text[:400]}')

        # 2) Subir el binario y obtener el handle.
        self.stdout.write('2/3 Subiendo la imagen…')
        r2 = requests.post(f'{base}/{session_id}',
                           headers={'Authorization': f'OAuth {token}', 'file_offset': '0'},
                           data=data, timeout=60)
        if r2.status_code >= 400:
            return self._fail(f'Error al subir la imagen: {r2.text[:400]}')
        handle = r2.json().get('h')
        if not handle:
            return self._fail(f'No se obtuvo el handle de la imagen: {r2.text[:400]}')

        # 3) Asignar la foto al perfil del número.
        self.stdout.write('3/3 Aplicando la foto al perfil…')
        r3 = requests.post(f'{base}/{pnid}/whatsapp_business_profile',
                           headers={'Authorization': f'Bearer {token}'},
                           json={'messaging_product': 'whatsapp', 'profile_picture_handle': handle},
                           timeout=30)
        if r3.status_code >= 400:
            return self._fail(f'Error al aplicar la foto: {r3.text[:400]}')

        self.stdout.write(self.style.SUCCESS(
            '✔ Foto de perfil del bot de WhatsApp actualizada. Puede tardar unos minutos '
            'en verse en los chats.'))
