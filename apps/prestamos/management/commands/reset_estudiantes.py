"""
Borra TODOS los estudiantes del sistema (espejo local), sin importar su origen.

Uso:
    python manage.py reset_estudiantes --dry-run   # solo muestra cuántos borraría
    python manage.py reset_estudiantes --si         # ejecuta el borrado

Estudiante = usuario con ficha de Estudiante o en el grupo 'Estudiante'. Se
EXCLUYEN superusuarios, staff y el personal (grupos Administrador/Recepcionista),
que se conservan. Al borrar el auth.User, la cascada arrastra su perfil, ficha,
reservas, préstamos y evidencias. No toca el inventario de Chromebooks ni los
mantenimientos. Pensado para dejar la base limpia antes de resincronizar la demo.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q


class Command(BaseCommand):
    help = 'Borra todos los estudiantes del espejo local (conserva personal/admin).'

    def add_arguments(self, parser):
        parser.add_argument('--si', action='store_true',
                            help='Confirma y ejecuta el borrado.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo informa cuántos registros se borrarían.')

    def _estudiantes_qs(self):
        return User.objects.filter(
            Q(perfil__estudiante__isnull=False) | Q(groups__name='Estudiante')
        ).exclude(
            Q(is_superuser=True) | Q(is_staff=True)
            | Q(groups__name__in=['Administrador', 'Recepcionista'])
        ).distinct()

    def handle(self, *args, **options):
        user_ids = list(self._estudiantes_qs().values_list('id', flat=True))
        total = len(user_ids)

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay estudiantes para borrar.'))
            return

        if options['dry_run'] or not options['si']:
            self.stdout.write(self.style.WARNING(
                f'Se borrarian {total} estudiantes y, por cascada, sus '
                f'reservas/prestamos/evidencias.'
            ))
            self.stdout.write('Ejecuta con --si para confirmar el borrado.')
            return

        with transaction.atomic():
            borrados, detalle = User.objects.filter(id__in=user_ids).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Eliminados {total} estudiantes. Objetos borrados en total: {borrados}.'
        ))
