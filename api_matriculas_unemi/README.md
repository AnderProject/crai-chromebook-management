# API de Matrículas UNEMI (simulador)

Proyecto Django **independiente** que simula el sistema de matrículas de la
UNEMI: es la *fuente de verdad* de los estudiantes. El sistema del CRAI lo
consume por API (`GET /api/estudiantes/<cédula>/` con header `X-API-KEY`) para
verificar y sincronizar estudiantes.

## Interfaz web (nueva)
En `http://localhost:8001/` hay un **panel profesional** para:
- **Matricular estudiantes** con todo lo que el CRAI necesita: cédula, nombres,
  apellidos, correo institucional, teléfono, facultad, carrera, semestre y
  estado de matrícula.
- **Buscar** por cédula/nombre/carrera, **cambiar el estado** de matrícula
  (activo/retirado/egresado) y **ocultar/mostrar** un estudiante en la API
  (para simular retiros).

## Cómo correrlo
Usa el mismo entorno del proyecto principal (ya incluye `djangorestframework`
y `Faker` vía `requirements.txt`):

```bash
# desde la raíz de proyecto_crai
env\Scripts\python.exe api_matriculas_unemi\manage.py runserver 8001
```

`iniciar_crai.bat` ya lo levanta automáticamente junto a Django/n8n/ngrok.

## Primera vez (la base SQLite no se sube al repo)
```bash
env\Scripts\python.exe api_matriculas_unemi\manage.py migrate
env\Scripts\python.exe api_matriculas_unemi\manage.py sembrar_demo   # 10 estudiantes demo
```

## Configuración que usa el CRAI (.env del proyecto principal)
```
API_MATRICULAS_BASE_URL=http://127.0.0.1:8001/api
API_MATRICULAS_KEY=clave-dev-compartida   # = API_KEY_MATRICULAS de esta API
```
