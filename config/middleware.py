"""Cabeçalhos de segurança extras: CSP e Permissions-Policy."""
from django.conf import settings

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",   # atributos style="" são usados nos templates
    "img-src 'self' data:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
PERMISSIONS = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resposta = self.get_response(request)
        # O painel administrativo do Django usa seus próprios scripts; fica fora da CSP.
        if not request.path.startswith("/" + settings.ADMIN_URL):
            resposta.headers.setdefault("Content-Security-Policy", CSP)
        resposta.headers.setdefault("Permissions-Policy", PERMISSIONS)
        return resposta
