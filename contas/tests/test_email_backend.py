import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.core.mail import send_mail
from django.test import TestCase, override_settings


class _Servidor:
    def __init__(self, status=201):
        self.status, self.recebido = status, {}
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers["Content-Length"])
                outer.recebido = {"headers": {k.lower(): v for k, v in self.headers.items()}, "body": json.loads(self.rfile.read(n))}
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"messageId":"x"}' if outer.status < 300 else b'{"code":"unauthorized"}')

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}/v3/smtp/email"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


class BrevoBackendTest(TestCase):
    def _cfg(self, srv, chave="chave-secreta"):
        return override_settings(EMAIL_BACKEND="contas.email_backends.BrevoEmailBackend",
                                 BREVO_API_KEY=chave, BREVO_API_URL=srv.url,
                                 DEFAULT_FROM_EMAIL="Trilha USP <contato@exemplo.com>")

    def test_envia_payload_correto(self):
        srv = _Servidor()
        try:
            with self._cfg(srv):
                n = send_mail("Assunto", "Corpo do e-mail", None, ["aluno@usp.br"])
            self.assertEqual(n, 1)
            r = srv.recebido
            self.assertEqual(r["headers"]["api-key"], "chave-secreta")
            self.assertEqual(r["body"]["to"], [{"email": "aluno@usp.br"}])
            self.assertEqual(r["body"]["sender"], {"email": "contato@exemplo.com", "name": "Trilha USP"})
            self.assertEqual(r["body"]["textContent"], "Corpo do e-mail")
        finally:
            srv.close()

    def test_erro_da_api_levanta_e_nao_vaza_chave_no_log(self):
        srv = _Servidor(status=401)
        try:
            with self._cfg(srv), self.assertLogs("contas.email_backends", level="ERROR") as cm:
                with self.assertRaises(Exception):
                    send_mail("A", "B", None, ["aluno@usp.br"])
            self.assertNotIn("chave-secreta", "".join(cm.output))
            self.assertIn("401", "".join(cm.output))
        finally:
            srv.close()

    def test_sem_chave_falha_claramente(self):
        srv = _Servidor()
        try:
            with self._cfg(srv, chave=""):
                with self.assertRaises(RuntimeError):
                    send_mail("A", "B", None, ["aluno@usp.br"])
        finally:
            srv.close()

    def test_fail_silently(self):
        srv = _Servidor(status=500)
        try:
            with self._cfg(srv):
                self.assertEqual(send_mail("A", "B", None, ["a@usp.br"], fail_silently=True), 0)
        finally:
            srv.close()
