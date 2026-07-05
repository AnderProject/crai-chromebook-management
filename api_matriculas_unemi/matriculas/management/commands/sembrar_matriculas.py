"""
Siembra la base de datos de matrículas con estudiantes falsos pero realistas.

Uso:
    python manage.py sembrar_matriculas                 # 200 estudiantes
    python manage.py sembrar_matriculas --cantidad 500
    python manage.py sembrar_matriculas --limpiar       # borra antes de sembrar

Simula que el sistema de matrículas de la UNEMI va registrando estudiantes.
Cada vez que se agregan, el sistema de reservas los verá al sincronizar.
"""
import random

from django.core.management.base import BaseCommand
from faker import Faker

from matriculas.models import EstudianteMatricula


# Oferta académica de la UNEMI (facultad -> carreras). Ajustable a la oferta vigente.
FACULTADES_CARRERAS = {
    'Facultad de Ciencias e Ingeniería': [
        'Ingeniería de Software',
        'Tecnologías de la Información',
        'Ingeniería Industrial',
        'Biotecnología',
    ],
    'Facultad de Ciencias de la Salud': [
        'Enfermería',
        'Nutrición y Dietética',
        'Fisioterapia',
        'Laboratorio Clínico',
    ],
    'Facultad de Ciencias de la Educación': [
        'Educación Básica',
        'Educación Inicial',
        'Pedagogía de la Actividad Física y Deporte',
        'Psicopedagogía',
    ],
    'Facultad de Ciencias Sociales, Educación Comercial y Derecho': [
        'Derecho',
        'Comunicación',
        'Economía',
        'Contabilidad y Auditoría',
        'Administración de Empresas',
        'Turismo',
    ],
}

ESTADOS_PONDERADOS = (
    ['activo'] * 17 + ['retirado'] * 2 + ['egresado'] * 1
)  # ~85% activos


def generar_cedula_ecuatoriana():
    """Genera una cédula ecuatoriana de 10 dígitos con dígito verificador válido."""
    provincia = random.randint(1, 24)
    digitos = [int(d) for d in f'{provincia:02d}']
    digitos.append(random.randint(0, 5))  # tercer dígito (persona natural)
    digitos += [random.randint(0, 9) for _ in range(6)]  # dígitos 4 al 9

    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for d, c in zip(digitos, coeficientes):
        producto = d * c
        suma += producto - 9 if producto > 9 else producto
    verificador = (10 - (suma % 10)) % 10
    digitos.append(verificador)
    return ''.join(str(d) for d in digitos)


class Command(BaseCommand):
    help = 'Siembra estudiantes matriculados de prueba (simula el sistema de la UNEMI).'

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=200,
                            help='Número de estudiantes a generar (default 200).')
        parser.add_argument('--limpiar', action='store_true',
                            help='Borra todos los estudiantes antes de sembrar.')

    def handle(self, *args, **options):
        fake = Faker('es_ES')
        cantidad = options['cantidad']

        if options['limpiar']:
            borrados, _ = EstudianteMatricula.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Eliminados {borrados} registros previos.'))

        cedulas_usadas = set(EstudianteMatricula.objects.values_list('cedula', flat=True))
        creados = 0
        intentos = 0
        max_intentos = cantidad * 5

        while creados < cantidad and intentos < max_intentos:
            intentos += 1
            cedula = generar_cedula_ecuatoriana()
            if cedula in cedulas_usadas:
                continue
            cedulas_usadas.add(cedula)

            facultad = random.choice(list(FACULTADES_CARRERAS.keys()))
            carrera = random.choice(FACULTADES_CARRERAS[facultad])
            nombres = fake.first_name()
            apellidos = f'{fake.last_name()} {fake.last_name()}'
            correo = f'{nombres.split()[0].lower()}.{apellidos.split()[0].lower()}@unemi.edu.ec'
            estado = random.choice(ESTADOS_PONDERADOS)

            EstudianteMatricula.objects.create(
                cedula=cedula,
                nombres=nombres,
                apellidos=apellidos,
                correo=correo,
                facultad=facultad,
                carrera=carrera,
                semestre=random.randint(1, 10),
                estado_matricula=estado,
                activo=(estado == 'activo'),
            )
            creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ {creados} estudiantes matriculados creados. '
            f'Total en BD: {EstudianteMatricula.objects.count()}.'
        ))
        # Muestra un par de ejemplos para probar login (usuario=cédula, contraseña=cédula).
        ejemplos = EstudianteMatricula.objects.filter(activo=True)[:3]
        if ejemplos:
            self.stdout.write('\n👉 Ejemplos para probar login (usuario y contraseña = cédula):')
            for e in ejemplos:
                self.stdout.write(f'   {e.cedula}  |  {e.apellidos} {e.nombres}  |  {e.carrera}')
