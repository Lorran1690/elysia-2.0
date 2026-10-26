// A visible fallback remains available even if React, Babel or JSX cannot load.
(function () {
  var root = document.getElementById('root');
  var timer;
  function failed(message) {
    if (window.elysiaMounted) return;
    document.getElementById('startup-title').textContent = 'Não foi possível abrir a interface';
    document.getElementById('startup-detail').textContent = message || 'Feche o aplicativo e extraia novamente o pacote completo.';
    document.getElementById('startup-reload').hidden = false;
  }
  window.addEventListener('error', function (event) {
    if (event.target && event.target.tagName === 'SCRIPT') failed('Uma biblioteca da interface não carregou. Extraia novamente o ZIP completo da versão mais recente.');
    else failed('Falha ao iniciar a interface: ' + (event.message || 'erro de JavaScript'));
  }, true);
  window.addEventListener('unhandledrejection', function () { failed('Falha ao iniciar a interface. Tente recarregar.'); });
  timer = setTimeout(function () { failed('A inicialização demorou além do esperado. Tente recarregar ou extraia novamente o pacote.'); }, 15000);
  var observer = new MutationObserver(function () {
    if (root.querySelector('.app')) {
      window.elysiaMounted = true; clearTimeout(timer); observer.disconnect();
      document.getElementById('startup').remove();
    }
  });
  observer.observe(root, {childList: true, subtree: true});
  document.getElementById('startup-reload').addEventListener('click', function () { window.location.reload(); });
})();
