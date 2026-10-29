from django import forms
from django.conf import settings

from .models import Usuario


class EmailForm(forms.Form):
    email = forms.EmailField(label="E-mail @usp.br", max_length=254,
                             widget=forms.EmailInput(attrs={"placeholder": "seunome@usp.br", "autocomplete": "email"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        dominio = email.rsplit("@", 1)[-1]
        if dominio not in settings.ALLOWED_EMAIL_DOMAINS:
            raise forms.ValidationError("Use seu e-mail institucional (@" + settings.ALLOWED_EMAIL_DOMAINS[0] + ").")
        return email


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["nome_exibicao", "ingresso_ano", "ingresso_semestre"]
        widgets = {"ingresso_ano": forms.NumberInput(attrs={"min": 2000, "max": 2100, "placeholder": "2024"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Depois de informado, o ingresso só muda pela administração (regra de quem pode contribuir).
        if self.instance and self.instance.ingresso_ano and self.instance.ingresso_semestre:
            for campo in ("ingresso_ano", "ingresso_semestre"):
                self.fields[campo].disabled = True
                self.fields[campo].help_text = "Para corrigir, fale com a equipe pelo formulário de contato."

    def clean_nome_exibicao(self):
        nome = " ".join(self.cleaned_data["nome_exibicao"].split())
        if len(nome) < 2:
            raise forms.ValidationError("Informe um nome de exibição.")
        return nome

    def clean(self):
        dados = super().clean()
        for campo in ("ingresso_ano", "ingresso_semestre"):
            if not dados.get(campo):
                self.add_error(campo, "Obrigatório.")
        return dados
