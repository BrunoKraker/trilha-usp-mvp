from django import forms

from .models import AvaliacaoDificuldade, Resumo


class ResumoForm(forms.ModelForm):
    class Meta:
        model = Resumo
        fields = ["tipo", "titulo", "corpo"]
        widgets = {"corpo": forms.Textarea(attrs={"rows": 8, "maxlength": 8000})}

    def clean_titulo(self):
        t = " ".join(self.cleaned_data["titulo"].split())
        if len(t) < 3:
            raise forms.ValidationError("Título muito curto.")
        return t

    def clean_corpo(self):
        c = self.cleaned_data["corpo"].strip()
        if len(c) < 30:
            raise forms.ValidationError("Escreva pelo menos algumas frases (mín. 30 caracteres).")
        return c


class NotaForm(forms.ModelForm):
    class Meta:
        model = AvaliacaoDificuldade
        fields = ["nota"]
