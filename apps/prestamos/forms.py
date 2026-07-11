import re
from django import forms
from .models import Chromebook

class ChromebookForm(forms.ModelForm):

    def clean_codigo(self):
        """Normaliza el código al formato CB-### (ej.: '012', '12', 'cb12' -> 'CB-012').

        Así el inventario queda consistente y la foto (que se busca por
        chromebooks/<codigo>.jpg) se encuentra correctamente.
        """
        codigo = (self.cleaned_data.get('codigo') or '').strip().upper()
        m = re.search(r'(\d+)', codigo)
        if m:
            codigo = f'CB-{int(m.group(1)):03d}'
        return codigo

    class Meta:
        model = Chromebook
        fields = ['codigo', 'marca', 'modelo', 'serie', 'estado', 'condicion',
                  'fecha_adquisicion', 'tiene_garantia', 'fecha_fin_garantia', 'notas', 'foto']
        widgets = {
            'fecha_adquisicion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin_garantia': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tiene_garantia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CB-001'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'HP, Lenovo, Dell...'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chromebook 11 G8'}),
            'serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de serie'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'condicion': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
        }