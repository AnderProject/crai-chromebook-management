"""
Deja la base de matrículas con EXACTAMENTE 10 estudiantes para la demo/tesis.

Uso:
    python manage.py sembrar_demo

Borra todos los registros previos e inserta 10 estudiantes: 4 con datos reales
acordados + 6 generados al azar. El correo se deriva del usuario institucional
(inicial 1er nombre + 1er apellido + inicial 2º apellido) @unemi.edu.ec.
"""
import random

from django.core.management.base import BaseCommand

from matriculas.models import EstudianteMatricula
from matriculas.utils import (
    generar_usuario, generar_telefono, generar_cedula_ecuatoriana,
)
from matriculas.management.commands.sembrar_matriculas import FACULTADES_CARRERAS

# Nombres ecuatorianos para los 6 estudiantes generados al azar.
NOMBRES_AZAR = [
    'Mateo Sebastian', 'Valentina Nicole', 'Joel Andres', 'Camila Doménica',
    'Santiago David', 'Emily Antonella', 'Bryan Alexander', 'Daniela Sofia',
]
APELLIDOS_AZAR = [
    'Vera Moreira', 'Zambrano Cedeno', 'Macias Bravo', 'Intriago Delgado',
    'Cevallos Mendoza', 'Santana Ponce', 'Alcivar Vera', 'Quijije Loor',
]

# Los 4 estudiantes acordados. cedula/telefono en None => se generan al azar.
ESTUDIANTES_FIJOS = [
    {
        'nombres': 'Anderson Alexander', 'apellidos': 'Merchan Balcazar',
        'cedula': '0957794324', 'telefono': '0978888939',
        'facultad': 'Facultad de Ciencias e Ingeniería',
        'carrera': 'Ingeniería de Software', 'semestre': 8,
    },
    {
        'nombres': 'Lady Paulet', 'apellidos': 'Loaiza Lozano',
        'cedula': None, 'telefono': None,
        'facultad': 'Facultad de Ciencias de la Salud',
        'carrera': 'Enfermería', 'semestre': 5,
    },
    {
        'nombres': 'Dary Jose', 'apellidos': 'Pincay Pinta',
        'cedula': None, 'telefono': None,
        'facultad': 'Facultad de Ciencias e Ingeniería',
        'carrera': 'Tecnologías de la Información', 'semestre': 6,
    },
    {
        'nombres': 'Nagerly Liliana', 'apellidos': 'Mercado Yumbo',
        'cedula': None, 'telefono': None,
        'facultad': 'Facultad de Ciencias Sociales, Educación Comercial y Derecho',
        'carrera': 'Comunicación', 'semestre': 4,
    },
]


class Command(BaseCommand):
    help = 'Deja la base con 10 estudiantes para la demo (borra todo lo previo).'

    def handle(self, *args, **options):
        borrados, _ = EstudianteMatricula.objects.all().delete()
        self.stdout.write(self.style.WARNING(f'Eliminados {borrados} registros previos.'))

        # 1) Construir la lista de los 10 (4 fijos + 6 al azar).
        plan = [dict(e) for e in ESTUDIANTES_FIJOS]

        nombres_azar = random.sample(NOMBRES_AZAR, 6)
        apellidos_azar = random.sample(APELLIDOS_AZAR, 6)
        for nombres, apellidos in zip(nombres_azar, apellidos_azar):
            facultad = random.choice(list(FACULTADES_CARRERAS.keys()))
            plan.append({
                'nombres': nombres, 'apellidos': apellidos,
                'cedula': None, 'telefono': None,
                'facultad': facultad,
                'carrera': random.choice(FACULTADES_CARRERAS[facultad]),
                'semestre': random.randint(1, 10),
            })

        # 2) Crear cada estudiante con cédula/teléfono/usuario/correo coherentes.
        cedulas = set()
        usuarios = set()
        creados = 0
        for e in plan:
            cedula = e['cedula']
            while not cedula or cedula in cedulas:
                cedula = generar_cedula_ecuatoriana()
            cedulas.add(cedula)

            usuario = generar_usuario(e['nombres'], e['apellidos'])
            usuario_unico, n = usuario, 2
            while usuario_unico in usuarios:
                usuario_unico = f'{usuario}{n}'
                n += 1
            usuarios.add(usuario_unico)

            EstudianteMatricula.objects.create(
                cedula=cedula,
                nombres=e['nombres'],
                apellidos=e['apellidos'],
                correo=f'{usuario_unico}@unemi.edu.ec',
                telefono=e['telefono'] or generar_telefono(),
                facultad=e['facultad'],
                carrera=e['carrera'],
                semestre=e['semestre'],
                estado_matricula='activo',
                activo=True,
            )
            creados += 1

        self.stdout.write(self.style.SUCCESS(f'{creados} estudiantes de demo creados.\n'))
        self.stdout.write('Credenciales (usuario = parte antes del @; contrasena inicial = cedula):')
        for est in EstudianteMatricula.objects.all().order_by('apellidos'):
            usuario = est.correo.split('@')[0]
            self.stdout.write(
                f'   {usuario:<14} | {est.cedula} | {est.apellidos} {est.nombres} | {est.telefono}'
            )
