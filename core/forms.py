from django import forms

from .models import MensagemContato


class ContatoForm(forms.ModelForm):
    # Campo-armadilha anti-spam: pessoas não veem; robôs preenchem.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))
    assunto = forms.ChoiceField(choices=[(a, a) for a in MensagemContato.ASSUNTOS])

    class Meta:
        model = MensagemContato
        fields = ["nome", "email", "assunto", "mensagem"]
        widgets = {"mensagem": forms.Textarea(attrs={"maxlength": 3000})}

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detectado.")
        return ""
