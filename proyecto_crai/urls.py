"""
URL configuration for proyecto_crai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render


def pagina_no_encontrada(request, *args, **kwargs):
    """Renderiza la página 404 personalizada para cualquier URL no encontrada
    (funciona también con DEBUG=True gracias al catch-all del final)."""
    return render(request, '404.html', status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('autenticacion:seleccionar_perfil')),
    path('autenticacion/', include('apps.autenticacion.urls')),
    path('prestamos/', include('apps.prestamos.urls')),
    path('estudiantes/', include('apps.estudiantes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Previsualización de las páginas de error (solo en desarrollo)
    urlpatterns += [
        path('preview/404/', lambda r: render(r, '404.html', status=404)),
        path('preview/500/', lambda r: render(r, '500.html', status=500)),
    ]

# Catch-all: cualquier URL no encontrada cae aquí y muestra la página 404 bonita.
# DEBE ir al final, después de admin, apps y archivos estáticos/media.
urlpatterns += [
    re_path(r'^.*$', pagina_no_encontrada),
]