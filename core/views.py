from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import ContatoForm


def pagina(template, nav):
    def view(request):
        return render(request, template, {"nav": nav})
    return view


def contato(request):
    form = ContatoForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Mensagem registrada. Retornaremos em até cinco dias úteis.")
            return redirect("core:contato")
        messages.error(request, "Revise os campos do formulário.")
    return render(request, "core/contato.html", {"form": form, "nav": "contato"})
