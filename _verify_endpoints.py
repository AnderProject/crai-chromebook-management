import json
from django.test import Client
from apps.prestamos.models import Estudiante

est = Estudiante.objects.select_related('usuario__user').first()
user = est.usuario.user
c = Client()
c.force_login(user)


def get(url):
    r = c.get(url, SERVER_NAME='localhost', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    ct = r.headers.get('Content-Type', '')
    if 'json' in ct:
        d = r.json()
        resumen = {k: (len(v) if isinstance(v, (str, dict, list)) else v) for k, v in d.items()}
        print(f"  [{r.status_code}] {url} -> {resumen}")
    else:
        print(f"  [{r.status_code}] {url} -> (no json) {r.content[:80]}")


print("== Portal ==")
get('/estudiantes/api/actividad/')
print("== Admin ==")
get('/prestamos/api/dashboard-stats/')
get('/prestamos/api/prestamos-hoy/')
get('/prestamos/api/chromebooks-estado/')
