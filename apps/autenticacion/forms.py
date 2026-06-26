# apps/autenticacion/forms.py

from django import forms
from django.contrib.auth.models import User

class FormularioLogin(forms.Form):
    """Formulario para el inicio de sesión"""
    usuario = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su usuario o correo electrónico',
            'id': 'id_usuario',
            'autocomplete': 'username'
        })
    )
    
    contraseña = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'id': 'id_contraseña',
            'autocomplete': 'current-password'
        })
    )

class FormularioRecuperarContraseña(forms.Form):
    """Formulario para recuperar/desbloquear contraseña mediante la cédula.

    Se valida que la cédula coincida con un usuario; el enlace de recuperación se
    envía al correo registrado de ese usuario. Sirve tanto para recuperar como
    para desbloquear una cuenta bloqueada por intentos fallidos.
    """
    cedula = forms.CharField(
        label='Número de Cédula',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su número de cédula',
            'id': 'id_cedula',
            'inputmode': 'numeric',
        })
    )

    def clean_cedula(self):
        cedula = (self.cleaned_data.get('cedula') or '').strip()
        if not cedula.isdigit() or len(cedula) != 10:
            raise forms.ValidationError('La cédula debe tener 10 dígitos.')
        return cedula