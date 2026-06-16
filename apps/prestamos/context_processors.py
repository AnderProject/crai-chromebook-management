def usuario_context(request):
    if request.user.is_authenticated:
        primer_nombre = request.user.first_name.split()[0] if request.user.first_name else 'Admin'
        primer_apellido = request.user.last_name.split()[0] if request.user.last_name else 'CRAI'
        return {
            'primer_nombre': primer_nombre,
            'primer_apellido': primer_apellido,
        }
    return {}