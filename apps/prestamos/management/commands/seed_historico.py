"""
Genera datos históricos de reservas y préstamos (abril–junio 2026) para que el
panel de Reportes tenga información realista, conservando los 10 estudiantes y
los 10 Chromebooks de la demo.

Borra SOLO los registros transaccionales (reservas, préstamos, evidencias,
mantenimientos y notificaciones). NO toca usuarios/estudiantes, Chromebooks,
carreras ni la configuración del sistema.

Uso:
    python manage.py seed_historico --dry-run   # informa qué haría
    python manage.py seed_historico --si          # ejecuta (borra + genera)

Distribución de los préstamos generados:
  - ~70 % devueltos a tiempo
  - ~18 % devueltos con atraso (cuentan como "no a tiempo")
  - ~12 % vencidos (estado 'vencido', sin devolver) -> alimentan la tasa de
    vencimiento y el ranking de estudiantes con vencidos.
Cada préstamo nace de una Reserva 'completada'. Además se crean algunas reservas
'vencida' sueltas (el estudiante reservó y no retiró el equipo).
"""
import random
import string
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.prestamos.models import (
    Estudiante, Chromebook, Reserva, Prestamo,
    Mantenimiento, Evidencia, Notificacion,
)

# Ventana histórica (hoy de la demo: 2026-06-23).
FECHA_INICIO = datetime(2026, 4, 1)
FECHA_FIN = datetime(2026, 6, 20)

N_PRESTAMOS = 110          # total de préstamos a generar
N_RESERVAS_VENCIDAS = 14   # reservas que el estudiante nunca retiró
N_MANTENIMIENTOS = 6

TECNICOS = ['Carlos Mendoza', 'Ana Torres', 'Luis Paredes']
PROBLEMAS = [
    'Pantalla con líneas verticales', 'Batería no carga', 'Teclado con teclas pegadas',
    'No enciende', 'Touchpad intermitente', 'Bisagra floja', 'Puerto USB dañado',
    'Sistema lento, requiere formateo',
]
MOTIVOS = [
    'Clase de programación', 'Investigación en biblioteca', 'Trabajo grupal',
    'Consulta de notas', 'Tarea de ofimática', 'Proyecto de titulación',
    'Examen en línea', 'Revisión bibliográfica',
]


class Command(BaseCommand):
    help = 'Genera reservas/préstamos históricos (abr–jun 2026) para los reportes.'

    def add_arguments(self, parser):
        parser.add_argument('--si', action='store_true', help='Confirma y ejecuta.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo informa, no modifica la base.')

    def handle(self, *args, **options):
        rng = random.Random(2026)  # determinista: misma demo en cada corrida
        tz = timezone.get_current_timezone()

        estudiantes = list(
            Estudiante.objects.select_related('usuario__user', 'carrera').all()
        )
        chromebooks = list(Chromebook.objects.all())

        if not estudiantes or not chromebooks:
            self.stderr.write(self.style.ERROR(
                'No hay estudiantes o Chromebooks. Aborto sin tocar nada.'
            ))
            return

        if options['dry_run'] or not options['si']:
            self.stdout.write(self.style.WARNING(
                'Se borrarían reservas, préstamos, evidencias, mantenimientos y '
                'notificaciones, y se generarían:\n'
                f'  - {N_PRESTAMOS} préstamos (con su reserva completada)\n'
                f'  - {N_RESERVAS_VENCIDAS} reservas vencidas sueltas\n'
                f'  - {N_MANTENIMIENTOS} mantenimientos finalizados\n'
                f'usando {len(estudiantes)} estudiantes y {len(chromebooks)} Chromebooks.'
            ))
            self.stdout.write('Ejecuta con --si para confirmar.')
            return

        codigos_usados = set()

        def codigo_unico():
            while True:
                c = ''.join(rng.choices(string.ascii_uppercase + string.digits, k=6))
                if c not in codigos_usados:
                    codigos_usados.add(c)
                    return c

        def dia_laboral():
            """Día aleatorio en la ventana, excluyendo domingos."""
            span = (FECHA_FIN - FECHA_INICIO).days
            while True:
                d = FECHA_INICIO + timedelta(days=rng.randint(0, span))
                if d.weekday() != 6:  # 6 = domingo
                    return d.date()

        with transaction.atomic():
            # --- Limpieza de datos transaccionales (conserva estudiantes/equipos) ---
            Evidencia.objects.all().delete()
            Prestamo.objects.all().delete()
            Reserva.objects.all().delete()
            Mantenimiento.objects.all().delete()
            Notificacion.objects.all().delete()

            n_a_tiempo = n_tarde = n_vencido = 0

            # --- Préstamos (cada uno con su reserva completada) ---
            for _ in range(N_PRESTAMOS):
                est = rng.choice(estudiantes)
                cb = rng.choice(chromebooks)
                user = est.usuario.user

                dia = dia_laboral()
                hora_ini = rng.randint(8, 14)          # jornada 8:00–17:00
                minuto = rng.choice([0, 30])
                duracion = rng.randint(2, 4)
                hora_fin = min(hora_ini + duracion, 17)

                inicio = timezone.make_aware(
                    datetime.combine(dia, time(hora_ini, minuto)), tz)
                devolucion = inicio + timedelta(hours=duracion)

                reserva = Reserva.objects.create(
                    estudiante=est,
                    carrera=est.carrera,
                    fecha_uso=dia,
                    hora_inicio=time(hora_ini, minuto),
                    hora_fin=time(hora_fin, minuto),
                    cantidad_solicitada=1,
                    estado='completada',
                    motivo=rng.choice(MOTIVOS),
                    codigo_verificacion=codigo_unico(),
                )

                r = rng.random()
                if r < 0.70:           # devuelto a tiempo
                    estado = 'devuelto'
                    devuelto = devolucion - timedelta(minutes=rng.randint(5, 90))
                    n_a_tiempo += 1
                elif r < 0.88:         # devuelto con atraso
                    estado = 'devuelto'
                    devuelto = devolucion + timedelta(hours=rng.randint(1, 30))
                    n_tarde += 1
                else:                  # vencido (nunca devuelto)
                    estado = 'vencido'
                    devuelto = None
                    n_vencido += 1

                Prestamo.objects.create(
                    estudiante=user,
                    chromebook=cb,
                    reserva=reserva,
                    fecha_prestamo=inicio,
                    fecha_devolucion=devolucion,
                    fecha_devuelto=devuelto,
                    estado=estado,
                    duracion_horas=duracion,
                    codigo_verificacion=codigo_unico(),
                    notas='Registro histórico (demo)',
                )

            # --- Reservas vencidas sueltas (no se retiró el equipo) ---
            for _ in range(N_RESERVAS_VENCIDAS):
                est = rng.choice(estudiantes)
                dia = dia_laboral()
                hora_ini = rng.randint(8, 14)
                minuto = rng.choice([0, 30])
                hora_fin = min(hora_ini + rng.randint(2, 4), 17)
                Reserva.objects.create(
                    estudiante=est,
                    carrera=est.carrera,
                    fecha_uso=dia,
                    hora_inicio=time(hora_ini, minuto),
                    hora_fin=time(hora_fin, minuto),
                    cantidad_solicitada=1,
                    estado='vencida',
                    motivo=rng.choice(MOTIVOS),
                    codigo_verificacion=codigo_unico(),
                )

            # --- Mantenimientos finalizados ---
            registrado_por = next(
                (e.usuario.user for e in estudiantes if e.usuario.user.is_staff), None
            )
            for _ in range(N_MANTENIMIENTOS):
                cb = rng.choice(chromebooks)
                dia = dia_laboral()
                dias_rep = rng.randint(1, 5)
                tipo = rng.choice(['preventivo', 'correctivo'])
                Mantenimiento.objects.create(
                    chromebook=cb,
                    tipo=tipo,
                    descripcion_problema=rng.choice(PROBLEMAS),
                    descripcion_solucion='Equipo revisado y devuelto a operación.',
                    tecnico=rng.choice(TECNICOS),
                    costo=Decimal(rng.choice(['0.00', '15.00', '25.50', '40.00', '60.00'])),
                    en_garantia=rng.random() < 0.3,
                    fecha_inicio=dia,
                    fecha_fin=dia + timedelta(days=dias_rep),
                    estado='finalizado',
                    registrado_por=registrado_por,
                )

            # --- Dejar el inventario en un estado coherente (todo disponible) ---
            Chromebook.objects.update(estado='disponible', condicion='bueno')

        self.stdout.write(self.style.SUCCESS(
            f'Histórico generado: {N_PRESTAMOS} préstamos '
            f'({n_a_tiempo} a tiempo, {n_tarde} con atraso, {n_vencido} vencidos), '
            f'{N_RESERVAS_VENCIDAS} reservas vencidas y {N_MANTENIMIENTOS} mantenimientos.'
        ))
        self.stdout.write(
            'Inventario reseteado a disponible/bueno. '
            'Los préstamos "vencidos" aparecerán también en el monitoreo en vivo; '
            'si no los quieres ahí, finalízalos desde el panel.'
        )
