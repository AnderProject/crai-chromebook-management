from django.db import models
from django.contrib.auth.models import User


# ==========================================
# TABLAS CATÁLOGO (NUEVAS)
# ==========================================

class Facultad(models.Model):
    """Facultades de la UNEMI"""
    nombre = models.CharField(max_length=150, unique=True, verbose_name='Nombre de Facultad')
    
    class Meta:
        db_table = 'tb_facultad'
        verbose_name = 'Facultad'
        verbose_name_plural = 'Facultades'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Carrera(models.Model):
    """Carreras universitarias"""
    facultad = models.ForeignKey(Facultad, on_delete=models.CASCADE, related_name='carreras')
    nombre = models.CharField(max_length=150, unique=True, verbose_name='Nombre de Carrera')
    
    class Meta:
        db_table = 'tb_carrera'
        verbose_name = 'Carrera'
        verbose_name_plural = 'Carreras'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class TipoUsuario(models.Model):
    """Roles del sistema"""
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre del Rol')
    
    class Meta:
        db_table = 'tb_tipo_usuario'
        verbose_name = 'Tipo de Usuario'
        verbose_name_plural = 'Tipos de Usuario'
    
    def __str__(self):
        return self.nombre


# ==========================================
# TABLAS DE USUARIOS (NUEVAS)
# ==========================================

class Usuario(models.Model):
    """Usuarios del sistema (extiende User de Django)"""

    ORIGEN_CHOICES = [
        ('local', 'Local'),
        ('api', 'API Matrículas'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo_usuario = models.ForeignKey(TipoUsuario, on_delete=models.PROTECT, verbose_name='Tipo de Usuario')
    cedula = models.CharField(max_length=10, unique=True, verbose_name='Cédula')
    telefono = models.CharField(max_length=10, blank=True, null=True, verbose_name='Teléfono')
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True, verbose_name='Foto de perfil')

    # Trazabilidad del espejo con la API de matrículas
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='local', verbose_name='Origen')
    matricula_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name='ID en Matrículas')
    sincronizado = models.DateTimeField(null=True, blank=True, verbose_name='Última sincronización')

    # Control de acceso: bloqueo por intentos fallidos y sesión única por usuario.
    intentos_fallidos = models.IntegerField(default=0, verbose_name='Intentos de login fallidos')
    cuenta_bloqueada = models.BooleanField(default=False, verbose_name='Cuenta bloqueada')
    session_key = models.CharField(max_length=40, blank=True, null=True, verbose_name='Sesión activa actual')

    class Meta:
        db_table = 'tb_usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Estudiante(models.Model):
    """Datos adicionales de estudiantes"""
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='estudiante')
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT, related_name='estudiantes')
    semestre = models.IntegerField(verbose_name='Semestre')
    
    class Meta:
        db_table = 'tb_estudiante'
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
    
    def __str__(self):
        return f'{self.usuario} - {self.carrera}'


# ==========================================
# CHROMEBOOK (SE MANTIENE IGUAL)
# ==========================================

class Chromebook(models.Model):
    """Inventario de Chromebooks"""
    
    ESTADOS = [
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('reservado', 'Reservado'),
        ('mantenimiento', 'Mantenimiento'),
    ]

    CONDICIONES = [
        ('bueno', 'Bueno'),
        ('regular', 'Regular'),
        ('malo', 'Malo'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    serie = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='disponible')
    condicion = models.CharField(max_length=20, choices=CONDICIONES, default='bueno')
    fecha_adquisicion = models.DateField(null=True, blank=True, verbose_name='Fecha de compra/adquisición')
    tiene_garantia = models.BooleanField(default=False, verbose_name='¿Tiene garantía?')
    fecha_fin_garantia = models.DateField(null=True, blank=True, verbose_name='Garantía válida hasta')
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    foto = models.ImageField(upload_to='chromebooks/', blank=True, null=True, verbose_name='Foto del equipo')
    ultimo_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name='Última conexión del kiosko')

    # Segundos de margen para considerar el equipo "en línea". La app kiosko hace
    # polling cada ~8-12s; con 60s damos holgura para reintentos/latencia.
    HEARTBEAT_UMBRAL_SEG = 60

    class Meta:
        db_table = 'tb_chromebook'
        verbose_name = 'Chromebook'
        verbose_name_plural = 'Chromebooks'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} - {self.marca} {self.modelo}'

    @property
    def esta_en_linea(self):
        """True si la app kiosko de este equipo contactó al servidor hace poco.

        Se basa en ``ultimo_heartbeat``, que se actualiza en cada consulta de la
        app al endpoint del kiosko. Si nunca ha contactado o pasó el umbral, se
        considera desconectado.
        """
        if not self.ultimo_heartbeat:
            return False
        from django.utils import timezone
        return (timezone.now() - self.ultimo_heartbeat).total_seconds() <= self.HEARTBEAT_UMBRAL_SEG

    @property
    def ultima_conexion_humana(self):
        """Texto amigable de cuándo fue la última conexión del kiosko."""
        if not self.ultimo_heartbeat:
            return 'Nunca'
        from django.utils import timezone
        seg = (timezone.now() - self.ultimo_heartbeat).total_seconds()
        if seg < 60:
            return 'Hace un momento'
        if seg < 3600:
            return f'Hace {int(seg // 60)} min'
        if seg < 86400:
            return f'Hace {int(seg // 3600)} h'
        return f'Hace {int(seg // 86400)} d'

    @property
    def en_garantia_vigente(self):
        """True si el equipo tiene garantía y aún no ha vencido (hoy <= fecha_fin).

        Si está marcado con garantía pero sin fecha de fin, se considera vigente
        (garantía sin caducidad registrada). Se usa para automatizar el costo de
        los mantenimientos: en garantía => costo 0.
        """
        if not self.tiene_garantia:
            return False
        if self.fecha_fin_garantia is None:
            return True
        from django.utils import timezone
        return self.fecha_fin_garantia >= timezone.localdate()


# ==========================================
# RESERVA (NUEVA)
# ==========================================

class Reserva(models.Model):
    """Reservas de Chromebooks"""
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
        ('vencida', 'Vencida'),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='reservas')
    carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT)
    fecha_uso = models.DateField(verbose_name='Fecha de Uso')
    hora_inicio = models.TimeField(verbose_name='Hora de Inicio')
    hora_fin = models.TimeField(verbose_name='Hora de Fin')
    cantidad_solicitada = models.IntegerField(default=1, verbose_name='Cantidad Solicitada')
    # Equipo específico apartado cuando la reserva se crea en recepción eligiendo una
    # Chromebook. Las reservas del portal/WhatsApp no eligen equipo (queda en null y al
    # confirmar se asigna la primera disponible).
    chromebook = models.ForeignKey(
        Chromebook, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reservas', verbose_name='Chromebook asignado'
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente', verbose_name='Estado')
    motivo = models.TextField(blank=True, null=True, verbose_name='Motivo')
    codigo_verificacion = models.CharField(max_length=6, unique=True, verbose_name='Código de Verificación')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def duracion_timedelta(self):
        """Duración exacta (timedelta) entre hora_inicio y hora_fin."""
        from datetime import datetime
        inicio = datetime.combine(self.fecha_uso, self.hora_inicio)
        fin = datetime.combine(self.fecha_uso, self.hora_fin)
        return fin - inicio

    def calcular_duracion(self):
        """Duración en horas entre hora_inicio y hora_fin.

        Devuelve un entero cuando es exacta (2) o un decimal cuando hay
        fracciones (0.5, 1.5). NO se trunca: media hora debe valer 0.5, no 0.
        """
        horas = self.duracion_timedelta().total_seconds() / 3600
        return int(horas) if horas == int(horas) else round(horas, 1)
    
    class Meta:
        db_table = 'tb_reserva'
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-creado']
    
    def __str__(self):
        return f'Reserva #{self.id} - {self.estudiante}'


# ==========================================
# PRÉSTAMO (SE MANTIENE TU ESTRUCTURA)
# ==========================================

class Prestamo(models.Model):
    """Registro de préstamos"""
    
    ESTADOS = [
        ('reservado', 'Reservado'),
        ('activo', 'Activo'),
        ('devuelto', 'Devuelto'),
        ('vencido', 'Vencido'),
    ]

    estudiante = models.ForeignKey(User, on_delete=models.CASCADE)
    chromebook = models.ForeignKey(Chromebook, on_delete=models.CASCADE)
    reserva = models.ForeignKey(Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos')
    fecha_prestamo = models.DateTimeField()
    fecha_devolucion = models.DateTimeField()
    fecha_devuelto = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')
    bloqueado = models.BooleanField(default=False, verbose_name='Bloqueado remotamente')
    duracion_horas = models.IntegerField(default=4)
    codigo_verificacion = models.CharField(max_length=6, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    qr_token = models.CharField(max_length=36, unique=True, null=True, blank=True)
    qr_tipo = models.CharField(max_length=20, null=True, blank=True)
    qr_expiracion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tb_prestamo'
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f'Préstamo #{self.id} - {self.estudiante.username}'

    @property
    def bloqueado_efectivo(self):
        """True si la Chromebook está (o debería estar) bloqueada ahora mismo:
        bloqueo remoto desde el dashboard, o préstamo activo cuyo tiempo ya venció
        (sigue 'activo' porque aún no se devuelve en el sistema)."""
        from django.utils import timezone
        if self.estado != 'activo':
            return False
        if self.bloqueado:
            return True
        return bool(self.fecha_devolucion and self.fecha_devolucion < timezone.now())


# ==========================================
# TABLAS DE SOPORTE (NUEVAS)
# ==========================================

class Evidencia(models.Model):
    """Fotos de entrega/devolución"""
    TIPOS = [
        ('entrega', 'Entrega'),
        ('devolucion', 'Devolución'),
        ('incidencia', 'Incidencia'),
    ]
    
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='evidencias')
    tipo = models.CharField(max_length=20, choices=TIPOS, verbose_name='Tipo de Evidencia')
    foto = models.ImageField(upload_to='evidencias/', blank=True, null=True, verbose_name='Foto')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Subida')
    
    class Meta:
        db_table = 'tb_evidencia'
        verbose_name = 'Evidencia'
        verbose_name_plural = 'Evidencias'
    
    def __str__(self):
        return f'Evidencia #{self.id} - {self.tipo}'


class Mantenimiento(models.Model):
    TIPOS = [
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
    ]
    
    ESTADOS = [
        ('en_proceso', 'En proceso'),
        ('finalizado', 'Finalizado'),
    ]
    
    chromebook = models.ForeignKey(Chromebook, on_delete=models.CASCADE, related_name='mantenimientos')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion_problema = models.TextField(blank=True, null=True)
    descripcion_solucion = models.TextField(blank=True, null=True)
    tecnico = models.CharField(max_length=150, blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    en_garantia = models.BooleanField(default=False, verbose_name='¿En garantía?')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='en_proceso')
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tb_mantenimiento'
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f'Mantenimiento #{self.id} - {self.chromebook}'


class Notificacion(models.Model):
    """Notificaciones del sistema"""
    TIPOS = [
        ('prestamo', 'Préstamo'),
        ('vencimiento', 'Vencimiento'),
        ('reserva', 'Reserva'),
        ('general', 'General'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS, default='general')
    leida = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tb_notificacion'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_envio']
    
    def __str__(self):
        return f'{self.tipo} - {self.titulo}'


class ChatbotConversacion(models.Model):
    """Historial del chatbot"""
    CANALES = [
        ('web', 'Web'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones', null=True, blank=True)
    mensaje_usuario = models.TextField()
    respuesta_bot = models.TextField(blank=True, null=True)
    canal = models.CharField(max_length=20, choices=CANALES, default='web')
    intencion_detectada = models.CharField(max_length=50, blank=True, null=True)
    fecha_interaccion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tb_chatbot_conversacion'
        verbose_name = 'Conversación del Chatbot'
        verbose_name_plural = 'Conversaciones del Chatbot'
        ordering = ['-fecha_interaccion']
    
    def __str__(self):
        return f'Chat #{self.id} - {self.canal}'
    

class SesionUsuario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField()
    navegador = models.CharField(max_length=255)
    sistema = models.CharField(max_length=100)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tb_sesion_usuario'
        verbose_name = 'Sesión de Usuario'
        verbose_name_plural = 'Sesiones de Usuario'
    
    def __str__(self):
        return f'{self.usuario.username} - {self.ip}'

class ConfiguracionSistema(models.Model):
    """Configuración global del sistema (fila única/singleton)."""
    api_matriculas_activa = models.BooleanField(
        default=True, verbose_name='Conexión con API de Matrículas activa'
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tb_configuracion_sistema'
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuración del Sistema'

    def __str__(self):
        return 'Configuración del sistema'

    @classmethod
    def obtener(cls):
        """Devuelve (creando si hace falta) la única fila de configuración."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
