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
    """Formulario para recuperar contraseña"""
    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico institucional',
            'id': 'id_email'
        })
    )