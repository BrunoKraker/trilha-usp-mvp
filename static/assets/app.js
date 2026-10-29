/* Comportamentos do MVP sem JavaScript inline (compatível com a CSP). */
(function () {
  // Confirmação antes de enviar formulários marcados com data-confirm="mensagem"
  document.addEventListener('submit', function (e) {
    var msg = e.target && e.target.getAttribute && e.target.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) e.preventDefault();
  });
  // Remove imagens que falharem ao carregar (marcadas com data-remove-on-error). O evento 'error' não
  // borbulha, por isso usamos a fase de captura. Também cobre imagens que já falharam antes do script rodar.
  document.addEventListener('error', function (e) {
    var el = e.target;
    if (el && el.tagName === 'IMG' && el.hasAttribute('data-remove-on-error')) el.remove();
  }, true);
  document.querySelectorAll('img[data-remove-on-error]').forEach(function (img) {
    if (img.complete && img.naturalWidth === 0) img.remove();
  });
})();
