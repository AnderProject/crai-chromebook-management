# -*- coding: utf-8 -*-
"""Portal de los técnicos del Departamento de TICs.

Login PROPIO (aparte del login principal del CRAI): el técnico entra con su
cédula y su contraseña (inicialmente su cédula). Desde aquí ve los
mantenimientos que le asignaron, confirma la reparación y sube la evidencia
(foto o video). Esa evidencia queda visible en el CRAI para que el personal
verifique y finalice el mantenimiento.
"""
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.utils import timezone

SESSION_KEY = 'tecnico_id'


def tecnico_actual(request):
    """Devuelve el Tecnico logueado en el portal (o None)."""
    from .models import Tecnico
    tid = request.session.get(SESSION_KEY)
    if not tid:
        return None
    return Tecnico.objects.filter(id=tid, activo=True).first()


def login_tecnico_requerido(vista):
    @wraps(vista)
    def wrapper(request, *args, **kwargs):
        tec = tecnico_actual(request)
        if tec is None:
            return redirect('prestamos:tecnico_login')
        return vista(request, tec, *args, **kwargs)
    return wrapper


def tecnico_login(request):
    """Login del portal de técnicos (cédula + contraseña)."""
    from .models import Tecnico

    if tecnico_actual(request) is not None:
        return redirect('prestamos:tecnico_panel')

    if request.method == 'POST':
        cedula = (request.POST.get('cedula') or '').strip()
        password = (request.POST.get('password') or '').strip()
        tecnico = Tecnico.objects.filter(cedula=cedula, activo=True).first()
        # Técnico sin contraseña asignada (legacy): su clave inicial es su cédula.
        if tecnico and not tecnico.password and password == tecnico.cedula:
            tecnico.set_password(cedula)
            tecnico.save(update_fields=['password'])
        if tecnico and tecnico.check_password(password):
            request.session[SESSION_KEY] = tecnico.id
            return redirect('prestamos:tecnico_panel')
        messages.error(request, 'Cédula o contraseña incorrectas.')

    return render(request, 'prestamos/tecnicos/login.html')


def tecnico_logout(request):
    request.session.pop(SESSION_KEY, None)
    return redirect('prestamos:tecnico_login')


@login_tecnico_requerido
def tecnico_panel(request, tecnico):
    """Panel del técnico: sus mantenimientos asignados."""
    from .models import Mantenimiento

    mantenimientos = (Mantenimiento.objects
                      .filter(tecnico_asignado=tecnico)
                      .select_related('chromebook')
                      .order_by('-fecha_inicio'))

    en_proceso = mantenimientos.filter(estado='en_proceso')
    contexto = {
        'tecnico': tecnico,
        'mantenimientos': mantenimientos,
        'total': mantenimientos.count(),
        'en_proceso': en_proceso.count(),
        'finalizados': mantenimientos.filter(estado='finalizado').count(),
        'por_confirmar': en_proceso.filter(confirmado_por_tecnico=False).count(),
    }
    return render(request, 'prestamos/tecnicos/panel.html', contexto)


@login_tecnico_requerido
def tecnico_confirmar(request, tecnico):
    """El técnico confirma la reparación y sube su evidencia (foto/video)."""
    from .models import Mantenimiento

    if request.method != 'POST':
        return redirect('prestamos:tecnico_panel')

    m = Mantenimiento.objects.filter(
        id=request.POST.get('mantenimiento_id'),
        tecnico_asignado=tecnico,
        estado='en_proceso',
    ).first()

    if m is None:
        messages.error(request, 'Mantenimiento no encontrado o ya finalizado.')
        return redirect('prestamos:tecnico_panel')

    solucion = (request.POST.get('descripcion_solucion') or '').strip()
    evidencia = request.FILES.get('evidencia')

    if not solucion:
        messages.error(request, 'Describe qué reparación realizaste.')
        return redirect('prestamos:tecnico_panel')
    if not evidencia:
        messages.error(request, 'Adjunta una foto o video como evidencia de la reparación.')
        return redirect('prestamos:tecnico_panel')

    m.descripcion_solucion = solucion
    m.evidencia_reparacion = evidencia
    m.confirmado_por_tecnico = True
    m.fecha_confirmacion_tecnico = timezone.now()
    m.save()

    messages.success(request, (
        f'¡Gracias! Registramos tu reparación de {m.chromebook.codigo}. '
        f'El CRAI la revisará y finalizará el mantenimiento.'
    ))
    return redirect('prestamos:tecnico_panel')


@login_tecnico_requerido
def tecnico_cambiar_password(request, tecnico):
    """Permite al técnico cambiar su contraseña."""
    if request.method == 'POST':
        actual = (request.POST.get('actual') or '').strip()
        nueva = (request.POST.get('nueva') or '').strip()
        confirmar = (request.POST.get('confirmar') or '').strip()
        if not tecnico.check_password(actual):
            messages.error(request, 'Tu contraseña actual no es correcta.')
        elif len(nueva) < 4:
            messages.error(request, 'La nueva contraseña debe tener al menos 4 caracteres.')
        elif nueva != confirmar:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            tecnico.set_password(nueva)
            tecnico.save(update_fields=['password'])
            messages.success(request, 'Contraseña actualizada.')
    return redirect('prestamos:tecnico_panel')


# ==========================================================================
# CORREO DE ASIGNACIÓN
# ==========================================================================

def _fecha_str(valor):
    """Formatea la fecha de inicio tanto si es date como si llega como texto."""
    try:
        return valor.strftime('%d/%m/%Y')
    except AttributeError:
        return str(valor or '')


def enviar_correo_asignacion(tecnico, mantenimiento, base_url):
    """Notifica por correo al técnico que se le asignó un mantenimiento."""
    if not tecnico or not tecnico.correo:
        return
    cb = mantenimiento.chromebook
    portal_url = f'{base_url}/prestamos/tecnicos/'
    fecha = _fecha_str(mantenimiento.fecha_inicio)
    asunto = f'Nuevo mantenimiento asignado · {cb.codigo}'
    texto = (
        f'Hola {tecnico.nombres}:\n\n'
        f'Se te asignó un mantenimiento en el CRAI de la UNEMI.\n\n'
        f'Equipo: {cb.codigo} ({cb.marca} {cb.modelo})\n'
        f'Tipo: {mantenimiento.get_tipo_display()}\n'
        f'Problema: {mantenimiento.descripcion_problema or "No especificado"}\n'
        f'Fecha de inicio: {fecha}\n\n'
        f'Ingresa a tu portal para confirmar la reparación y subir la evidencia:\n'
        f'{portal_url}\n\n'
        f'Usuario: tu cédula ({tecnico.cedula}). Si es tu primer ingreso, la '
        f'contraseña también es tu cédula.\n\n'
        f'— Departamento de TICs · CRAI UNEMI'
    )
    html = _html_correo_asignacion(tecnico, mantenimiento, portal_url)
    try:
        msg = EmailMultiAlternatives(asunto, texto, settings.DEFAULT_FROM_EMAIL, [tecnico.correo])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass


def _html_correo_asignacion(tecnico, m, portal_url):
    cb = m.chromebook
    fecha = _fecha_str(m.fecha_inicio)
    return f"""\
<!DOCTYPE html><html lang="es"><body style="margin:0;padding:0;background:#eef2f8;font-family:'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f8;padding:28px 12px;"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(13,44,84,0.12);">
  <tr><td style="background:linear-gradient(120deg,#0d2c54,#14417b 70%,#1b5aa8);padding:28px 34px;">
    <div style="font-size:24px;font-weight:800;color:#fff;letter-spacing:3px;">UNEMI</div>
    <div style="font-size:13px;color:#f2a900;font-weight:600;margin-top:4px;">CRAI · Departamento de TICs</div>
  </td></tr>
  <tr><td style="padding:32px 34px;">
    <h1 style="margin:0 0 6px;font-size:20px;color:#0d2c54;">Nuevo mantenimiento asignado</h1>
    <p style="margin:0 0 18px;font-size:15px;color:#3a4658;">Hola <strong>{tecnico.nombres}</strong>, se te asignó la reparación de un equipo:</p>
    <table role="presentation" width="100%" style="border:1px solid #e3eaf4;border-radius:12px;border-collapse:separate;overflow:hidden;font-size:14px;color:#3a4658;">
      <tr><td style="padding:10px 14px;background:#f6f9ff;font-weight:700;width:130px;">Equipo</td><td style="padding:10px 14px;">{cb.codigo} · {cb.marca} {cb.modelo}</td></tr>
      <tr><td style="padding:10px 14px;background:#f6f9ff;font-weight:700;">Tipo</td><td style="padding:10px 14px;">{m.get_tipo_display()}</td></tr>
      <tr><td style="padding:10px 14px;background:#f6f9ff;font-weight:700;">Problema</td><td style="padding:10px 14px;">{m.descripcion_problema or 'No especificado'}</td></tr>
      <tr><td style="padding:10px 14px;background:#f6f9ff;font-weight:700;">Fecha</td><td style="padding:10px 14px;">{fecha}</td></tr>
    </table>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0;"><tr><td align="center" style="border-radius:12px;background:linear-gradient(120deg,#14417b,#1b5aa8);">
      <a href="{portal_url}" target="_blank" style="display:inline-block;padding:14px 34px;color:#fff;font-size:15px;font-weight:700;text-decoration:none;border-radius:12px;">Ir a mi portal de técnico</a>
    </td></tr></table>
    <p style="margin:0;font-size:13px;color:#7b8794;">Ingresa con tu cédula (<strong>{tecnico.cedula}</strong>). En tu primer acceso, la contraseña también es tu cédula.</p>
  </td></tr>
  <tr><td style="background:#f4f7fb;padding:16px 34px;border-top:1px solid #e3eaf4;"><p style="margin:0;font-size:12px;color:#9aa5b1;">Universidad Estatal de Milagro · CRAI · Correo automático, no respondas.</p></td></tr>
</table></td></tr></table></body></html>"""
