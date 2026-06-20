"""Filtros de plantilla para control de acceso por rol."""
from django import template

register = template.Library()


@register.filter
def es_tics(user):
    """True si el usuario es TICs/administrador (puede gestionar personal)."""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Tics']).exists()
