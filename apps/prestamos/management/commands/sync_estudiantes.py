"""
Sincroniza el espejo local de estudiantes con la API de matrículas.

Uso:
    python manage.py sync_estudiantes                 # sincroniza TODOS
    python manage.py sync_estudiantes --cedula 0102030405   # solo uno

Pensado para correrse periódicamente (cron / tarea programada) de modo que cuando
matrícula agrega o modifica estudiantes, el sistema de reservas se actualice solo.
"""
from django.core.management.base import BaseCommand

from apps.prestamos.services.api_estudiantes import (
    obtener_estudiante, listar_estudiantes, ApiEstudiantesError,
)
from apps.prestamos.services.sincronizacion import sincronizar_estudiante


class Command(BaseCommand):
    help = 'Sincroniza estudiantes desde la API de matrículas hacia el espejo local.'

    def add_arguments(self, parser):
        parser.add_argument('--cedula', help='Sincroniza solo la cédula indicada.')

    def handle(self, *args, **options):
        cedula = options.get('cedula')

        if cedula:
            self._sync_uno(cedula)
            return

        self._sync_todos()

    def _sync_uno(self, cedula):
        try:
            data = obtener_estudiante(cedula)
        except ApiEstudiantesError as exc:
            self.stderr.write(self.style.ERROR(f'❌ API no disponible: {exc}'))
            return

        if data is None:
            self.stdout.write(self.style.WARNING(f'⚠️  {cedula}: no existe en matrículas.'))
            return

        _, creado = sincronizar_estudiante(data)
        accion = 'creado' if creado else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'✅ {cedula} {accion}.'))

    def _sync_todos(self):
        try:
            estudiantes = listar_estudiantes()
        except ApiEstudiantesError as exc:
            self.stderr.write(self.style.ERROR(f'❌ API no disponible: {exc}'))
            return

        creados = actualizados = errores = 0
        for data in estudiantes:
            try:
                _, creado = sincronizar_estudiante(data)
                if creado:
                    creados += 1
                else:
                    actualizados += 1
            except Exception as exc:  # noqa: BLE001 - no abortar el lote por un registro
                errores += 1
                self.stderr.write(self.style.WARNING(
                    f'⚠️  Error con {data.get("cedula", "?")}: {exc}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'✅ Sincronización completa. '
            f'Creados: {creados}, actualizados: {actualizados}, errores: {errores}. '
            f'Total recibidos: {len(estudiantes)}.'
        ))
